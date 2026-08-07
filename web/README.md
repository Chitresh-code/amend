# Amend Web

React + TypeScript + Vite, routed with React Router. See the [repository root README](../README.md) for the monorepo overview and [../docs/](../docs/) for product requirements, architecture, and schema. Delivery plan: [../docs/internal/epics-web-mvp.md](../docs/internal/epics-web-mvp.md).

## Development

```bash
cd web
npm install
npm run dev
npm run lint
npm run build
```

`npm run build` type-checks (`tsc -b`) before bundling. There is no test runner configured yet; add one when a component has behavior worth testing beyond type checking.
