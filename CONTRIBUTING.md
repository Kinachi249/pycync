# Contributing Code
Thank you for considering adding a contribution to the project!

If you would like to make a code contribution, first start out by forking the repository. Then, create a new branch in your fork that will contain your code changes.

Once your code is finished, you can open a pull request for your branch that is pointed to this repository's `main` branch.

## Pull Request Prerequisites
When working on your code change, please keep these points in mind before putting up your pull request! If all the points aren't covered, we may ask for additional work to be done.
- If you are adding or changing logic in the packet builders or packet parsers, unit tests are *required* be written that cover the new functionality and potential edge cases.
  - These parsers are pretty complex, so having unit tests ensure that they stay functional and are more protected against future regressions.
  - If you are adding/changing functionality outside of these modules, unit tests are still *highly encouraged*.
- If you are changing how existing parser functions work, please include where you sourced your change from in the PR description, even if it is self research/observations.
  - Since this library is a product of reverse engineering, we want to make sure that the reasoning and observations that led to the changes are sound.
- For any other changes, please have a brief description in your PR summarizing why the change was made. Context is always important!
- If you are modifying information in the device capabilities or device types modules, the changes *must* be sourced directly from the Cync app code.
  - This ensures that the device information is coming from a source of truth.
  - In addition, ensure you update the docstring at the top of the module to include the app version that the new info was fetched from.
 
After the code is reviewed and looks good, it will be merged and included in the next release.

Thanks so much for your interest in helping out!
