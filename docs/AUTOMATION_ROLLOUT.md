# Automation rollout and publish guide

The design is prepared locally. No commit or push is performed by this redesign session.

## Active workflows

### `validate-profile.yml`

Runs on relevant pull requests, pushes to `main`, or manually. It validates local README references, SVG XML, light/dark asset pairs, JSON configuration, Python syntax, private-source exclusions, and legacy-file removal. It requires read-only repository access.

### `profile-assets.yml`

Runs every 12 hours, manually, or when an asset generator/config changes. It:

1. Checks out the profile repository.
2. Uses Python 3.13.
3. Fetches public profile, repository, language, and contribution data.
4. Regenerates light/dark radars, statistics, languages, achievements, project cards, infrastructure banner, automation loop, and 3D calendar.
5. Validates the complete generated profile.
6. Commits only when generated content changed.

The workflow uses the repository's built-in `GITHUB_TOKEN` with `contents: write`. No personal access token is required.

### `snake.yml`

Runs daily and publishes light/dark snake SVGs to the `output` branch. It also uses only the built-in `GITHUB_TOKEN`.

## First publish

1. Review `git diff` and confirm the portrait, radar values, project order, and wording.
2. Create a feature branch and push it.
3. Open a pull request rather than pushing directly to `main`.
4. Preview the rendered README on GitHub in light and dark mode and at phone width.
5. Merge after visual approval.
6. Open **Actions → Refresh profile assets → Run workflow**.
7. Open **Actions → Generate contribution snake → Run workflow**.
8. Confirm the generated commit and `output` branch.

The profile becomes live when the pull request is merged into the special `RahulSinghParmar/RahulSinghParmar` repository. A GitHub Release is optional and does not control profile activation. If you want a named design milestone, create tag `v1.0.0` and a short GitHub Release only after the production README has been visually approved.

If a workflow cannot push, open **Settings → Actions → General → Workflow permissions** and enable **Read and write permissions**.

## Spotify binding

Spotify is active through a theme-matched hosted SVG card. Only the public card UID is stored in the README; Spotify access and refresh tokens are not repository secrets.

If Spotify access is revoked or expires:

1. Open `https://spotify-github-profile.kittinanx.com/api/login`.
2. Sign in and approve read-only access to currently playing and recently played music.
3. Copy the generated `uid` value from the success page.
4. Verify both theme-matched `api/view` endpoints return `image/svg+xml`.
5. Update the README only if the generated UID changed.

Do not commit Spotify client secrets or refresh tokens. A hosted card requires no repository secret after the one-time OAuth connection.

## Data and secret matrix

| Feature | Binding | Secret required |
| --- | --- | --- |
| GitHub cards, radars, language mix, projects | GitHub REST API | Built-in `GITHUB_TOKEN` only |
| 3D contribution calendar | Public contribution history API | No |
| Snake | GitHub Actions + `output` branch | Built-in `GITHUB_TOKEN` only |
| Spotify hosted card | One-time Spotify OAuth; public card UID in README | No repository secret |
| Portrait generation | Private local source photo | No; source stays ignored |

## Failure and rollback behavior

- A GitHub/API refresh retries three times and falls back to `assets/profile-data.json`.
- Generated assets are committed, so the last successful visuals remain available during service outages.
- To pause refreshes, disable the workflow from the Actions page; the profile continues serving checked-in assets.
- To roll back a design, revert the profile commit. Do not delete the `output` branch unless the snake is intentionally removed.
