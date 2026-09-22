# CodeRabbit reviews

The repository's `.coderabbit.yaml` configures CodeRabbit for this offline Python
game: simulation correctness, save compatibility, finances, time controls, and
the terminal and local browser interfaces.

## Activate

1. Install the [CodeRabbit GitHub App](https://github.com/apps/coderabbitai)
   and select `JR-4B3/GameDev` under **Only select repositories**.
2. Commit and push `.coderabbit.yaml`, and merge it into `main` so future branches
   include the configuration.
3. Open a non-draft pull request targeting `main`. CodeRabbit should post a review
   and review subsequent pushes automatically, subject to service limits.

CodeRabbit advertises free reviews for public repositories; this repository is
public. No model API key or GitHub Actions workflow is required. See the
[current pricing FAQ](https://www.coderabbit.ai/pricing) for plan details.

## Everyday use

- Develop on a branch and open a pull request; direct pushes to `main` do not
  trigger this PR-review workflow.
- Comment `@coderabbitai review` on a pull request to request a review manually.
- Reply to a review comment to ask for clarification or explain intended behavior.
- Continue running the existing Python tests and browser checks. Reviews supplement
  testing and playtesting; they do not verify game balance or visual quality.

If no review appears, check the app's repository access, whether the PR is a draft,
and the CodeRabbit review status comment or dashboard.
