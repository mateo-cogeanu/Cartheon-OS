# Repository instructions

- Every repository change must update `CHANGELOG.md` in the same commit.
- Add each entry under `Unreleased` with a Europe/Prague ISO 8601 timestamp in the
  form `YYYY-MM-DDTHH:MM:SS+HH:MM`; never rewrite an older timestamp.
- Describe the user-visible or build-visible result with concise bullet points.
- Run `make test` and `make lint` after changing Python code or cartridge behavior.
- Run shell syntax checks after changing build, packaging, or live-image scripts.
- Do not commit generated kernels, Debian packages, ISO images, caches, or secrets.
