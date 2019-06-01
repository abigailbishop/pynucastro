#!/bin/bash
set -e # Exit with nonzero exit code if anything fails

# Then we Build and deploy the sphinx documentation
SOURCE_BRANCH="master"
TARGET_BRANCH="gh-pages"

# Pull requests and commits to other branches shouldn't try to deploy
if [ "$TRAVIS_PULL_REQUEST" != "false" -o "$TRAVIS_BRANCH" != "$SOURCE_BRANCH" ]; then
    echo "Skipping deploy on $TRAVIS_BRANCH. We only deploy docs automatically from master."
    exit 0
fi

# Save some useful information
REPO=`git config remote.origin.url`
SSH_REPO=${REPO/https:\/\/github.com\//git@github.com:}
SHA=`git rev-parse --verify HEAD`

# Add rsa keys to the ssh agent to push to GitHub
gpg --output ../id_rsa_pynucastro_deploy --batch --passphrase $DECRYPT_GITHUB_AUTH --decrypt id_rsa_pynucastro_deploy.enc
chmod 600 ../id_rsa_pynucastro_deploy
eval `ssh-agent -s`
ssh-add ../id_rsa_pynucastro_deploy

# Clone the existing gh-pages for this repo into out/
# Create a new empty branch if gh-pages doesn't exist yet (should only happen on first deply)
git clone $REPO out
cd out

# Regenerate the API documentation
git checkout $SOURCE_BRANCH || git checkout --orphan $SOURCE_BRANCH
sphinx-apidoc -f -M -o docs/source/ .

# Add new docs to the repo
git add docs/source --all

# Commit and push to SOURCE_BRANCH
git commit -m "Regenerate API Documentation: ${SHA}" || true
git push $SSH_REPO $SOURCE_BRANCH || true

git checkout $TARGET_BRANCH || git checkout --orphan $TARGET_BRANCH
cd ..

# Clean out existing contents
rm -rf out/**/* || exit 0

# Pull from SOURCE_BRANCH again
git pull || true

# Build the Sphinx documentation
cd docs
make html
cd ../

mv docs/build/html/* out/
touch out/.nojekyll

# Now let's go have some fun with the cloned repo
cd out
git config user.name "Travis CI"
git config user.email "$COMMIT_AUTHOR_EMAIL"

if git diff-index --quiet HEAD; then
    exit 0
fi

# Commit the "changes", i.e. the new version.
# The delta will show diffs between new and old versions.
git add --all
git commit -m "Deploy to GitHub Pages: ${SHA}" || true
git push $SSH_REPO $TARGET_BRANCH || true
cd ..

# Kill the ssh-agent
ssh-agent -k
