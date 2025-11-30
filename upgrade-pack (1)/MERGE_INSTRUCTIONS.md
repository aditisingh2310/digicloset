# Merge checklist (suggested)
- [ ] Run `npm ci` and `npm run test` locally
- [ ] Ensure `package.json` contains test and lint scripts:
      "test": "jest",
      "lint": "eslint ."
- [ ] Add CODEOWNERS to enforce reviews
- [ ] Add GitHub secrets: DOCKER_REGISTRY, DOCKER_USERNAME, DOCKER_PASSWORD, KUBECONFIG (if used)
- [ ] Enable branch protection on main with required status checks for CI and CodeQL
