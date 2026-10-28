# PEAKS website · staging

A test copy of [peaks-office.ch](https://peaks-office.ch) that is **not live**. Changes are made and checked here first,
then copied to the live site in one step.

- **Staging site:** https://marcelsteimke.github.io/peaks-website-staging/
- **Live site:** https://peaks-office.ch, from the repo `peaks-impact/peaks-impact.gibhub.io`

## How it works

1. Edit and push to `main` here. The staging site updates in about a minute.
2. Every staging page carries a red "STAGING" badge and a `noindex` tag, both between
   `<!-- STAGING:START -->` and `<!-- STAGING:END -->`, so search engines skip it and nobody mistakes it for the real site.
3. When it looks right, `./promote-to-live.sh` copies everything into a checkout of the live repo, strips the staging
   markers, checks every link, image, font and anchor with `check-links.py`, and shows the diff.
   `./promote-to-live.sh --push` publishes it. A broken link stops both.

The live repo's `CNAME` (peaks-office.ch) is never touched, and this README and the two scripts never go live.
Forms and links on staging point to the real services (the Airtable application form, Luma), so a test
submission there is a real submission.
