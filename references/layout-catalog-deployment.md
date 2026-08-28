# Layout Catalog Deployment

Remote publication changes shared state. Do not deploy unless the user has explicitly authorized publication for the current task.

## Gate

1. Resolve the requested project, branch, host, path, and exact URL. The main Cloudflare Pages project is `layout-catalog` unless the user names another verified target.
2. Inspect Git and artifact status. Do not publish a mixed dirty worktree and do not use `--commit-dirty=true`.
3. Build from a clean approved snapshot or isolated worktree that contains only the intended deploy inputs.
4. If the catalog links to a dependency site, rebuild and verify that site before the parent catalog.

## Build and Verify

```powershell
python scripts\generate_layout_gallery.py
python scripts\verify_layout_gallery_triptychs.py
python scripts\convert_deploy_png_to_webp.py --quality 84
```

Confirm that every main-gallery preview has a latest `pass` QA record or explicit human approval. Keep original PNG sources while gallery and review pages prefer WebP.

## Deploy

After the authorization and clean-snapshot gates pass:

```powershell
npx wrangler pages deploy <verified-deploy-dir> --project-name layout-catalog
```

Do not push, create a PR, or mutate another remote unless the user separately authorizes it.

## Exact URL Verification

Fetch the complete user-specified URL after deployment and compare it with the approved local artifact using SHA-256 or an equivalent content check. Wrangler success, a production homepage, or local file existence does not prove that an exact host/path is correct.

Report the source commit or snapshot, build checks, deployed target, exact-URL evidence, and every unverified item.
