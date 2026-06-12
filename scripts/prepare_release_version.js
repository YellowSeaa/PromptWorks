#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const releaseVersion = process.argv[2];

if (!releaseVersion) {
  console.error("用法：node scripts/prepare_release_version.js <release-version>");
  process.exit(1);
}

const root = path.resolve(__dirname, "..");
const normalizedVersion = releaseVersion.replace(/^v/, "");
const displayVersion = `v${normalizedVersion}`;

function updateJsonFile(relativePath, updater) {
  const filePath = path.join(root, relativePath);
  const content = JSON.parse(fs.readFileSync(filePath, "utf8"));
  updater(content);
  fs.writeFileSync(filePath, `${JSON.stringify(content, null, 2)}\n`, "utf8");
}

updateJsonFile("package.json", (pkg) => {
  pkg.version = normalizedVersion;
});

updateJsonFile("package-lock.json", (lockfile) => {
  lockfile.version = normalizedVersion;
  if (lockfile.packages && lockfile.packages[""]) {
    lockfile.packages[""].version = normalizedVersion;
  }
});

fs.writeFileSync(
  path.join(root, "frontend", "src", "version.json"),
  `${JSON.stringify({ version: displayVersion })}\n`,
  "utf8",
);
