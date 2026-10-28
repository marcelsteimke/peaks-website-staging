#!/usr/bin/env python3
"""Checks every link, image, font and #anchor on the site's pages. promote-to-live.sh runs it before anything goes live.

    python3 check-links.py [site folder]

Files of the site itself (also when written as https://peaks-office.ch/...) must exist in the folder, #anchors must
exist on their page, and every other address must answer. Exits with 1 if anything is broken. Sites that turn away
scripts (403, 429 and the like) only get a warning, since they usually open fine in a browser.
"""
import concurrent.futures as cf
import html.parser
import pathlib
import re
import subprocess
import sys
import time
import urllib.parse

SITE = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
DOMAIN = (SITE / 'CNAME').read_text().strip() if (SITE / 'CNAME').exists() else 'peaks-office.ch'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
TURNS_SCRIPTS_AWAY = {401, 403, 405, 429, 451, 999}


class Page(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.ids, self.css, self.in_style = [], set(), [], False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'):
            self.ids.add(a['id'])
        if tag != 'base':   # <base> only says where the page's links start; the pages all sit at the site root
            self.refs += [a[k] for k in ('href', 'src') if a.get(k)]
        if tag == 'meta' and (a.get('content') or '').startswith(('http://', 'https://')):
            self.refs.append(a['content'])   # og:image, og:url
        self.in_style = tag == 'style'

    def handle_endtag(self, tag):
        if tag == 'style':
            self.in_style = False

    def handle_data(self, data):
        if self.in_style:
            self.css.append(data)


def site_file(path):
    """The file a path on this site points to, or None."""
    p = SITE.joinpath(*[s for s in urllib.parse.unquote(path).split('/') if s not in ('', '.')])
    if p.is_dir():
        p = p / 'index.html'
    return p if p.is_file() else None


pages = {p.name: Page() for p in sorted(SITE.glob('*.html'))}
for name, page in pages.items():
    page.feed((SITE / name).read_text(encoding='utf-8'))

problems, warnings, web, checked, stylesheets = [], [], {}, set(), set()


def check(ref, where, folder=''):
    if (ref, where) in checked:
        return
    checked.add((ref, where))
    if ref.startswith('#'):
        if ref[1:] not in pages[where.split(' ')[0]].ids:
            problems.append(f'{where}: no element with id "{ref[1:]}" for {ref}')
        return
    if ref.startswith('mailto:'):
        if not re.fullmatch(r'mailto:[\w.+-]+@[\w-]+(\.[\w-]+)+', ref):
            problems.append(f'{where}: malformed email link {ref}')
        return
    if ref.startswith(('data:', 'tel:')):
        return
    u = urllib.parse.urlsplit(ref)
    if u.scheme in ('http', 'https') and u.hostname not in (DOMAIN, 'www.' + DOMAIN):
        web.setdefault(ref, where)
        return
    path = u.path if u.scheme else folder + u.path
    f = site_file(path)
    if not f:
        problems.append(f'{where}: {ref} is missing from the site')
    elif u.fragment and f.name in pages and u.fragment not in pages[f.name].ids:
        problems.append(f'{where}: {f.name} has no element with id "{u.fragment}" for {ref}')
    elif f.suffix == '.css' and f not in stylesheets:   # fonts and images a stylesheet loads, checked once per stylesheet
        stylesheets.add(f)
        for inner in re.findall(r'url\(\s*[\'"]?([^\'")]+)', f.read_text(encoding='utf-8')):
            check(inner, f'{where} via {f.relative_to(SITE)}', str(f.parent.relative_to(SITE)) + '/')


def answer(url):
    code = 0
    for attempt in range(2):
        r = subprocess.run(['curl', '-s', '-o', '/dev/null', '-L', '--max-time', '20', '-A', UA, '-w', '%{http_code}', url],
                           capture_output=True, text=True)
        code = int(r.stdout or 0)
        if 200 <= code < 400 or code in TURNS_SCRIPTS_AWAY:
            break
        time.sleep(2)
    return code


for name, page in pages.items():
    for ref in page.refs:
        check(ref, name)
    for ref in re.findall(r'url\(\s*[\'"]?([^\'")]+)', ''.join(page.css)):
        check(ref, name)

with cf.ThreadPoolExecutor(10) as ex:
    for url, code in zip(web, ex.map(answer, web)):
        if code in TURNS_SCRIPTS_AWAY:
            warnings.append(f'{web[url]}: {url} answered {code} to the script; check it once in a browser')
        elif not 200 <= code < 400:
            problems.append(f'{web[url]}: {url} ' + (f'answered {code}' if code else 'did not answer'))

print(f'Link check: {len(checked)} links, images, fonts and anchors in {", ".join(pages)}, {len(web)} of them on other sites')
for w in warnings:
    print('  !', w)
for p in problems:
    print('  ✗', p)
if not problems:
    print('  ✓ nothing broken')
sys.exit(1 if problems else 0)
