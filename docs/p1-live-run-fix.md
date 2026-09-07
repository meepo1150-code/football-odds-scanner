# P1 live-run trigger fix

This change enables live research execution on pushes to `main` and allows the dashboard workflow to request GitHub Pages enablement. Generated research outputs are excluded from the push trigger to prevent workflow loops.
