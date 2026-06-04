const path = require("path");

const patchPath = path.resolve(__dirname, "node-readlink-patch.cjs");
const requirePatch = `--require ${JSON.stringify(patchPath)}`;
process.env.NODE_OPTIONS = [requirePatch, process.env.NODE_OPTIONS].filter(Boolean).join(" ");
require(patchPath);

process.argv = [process.argv[0], require.resolve("next/dist/bin/next"), "build"];
require("next/dist/bin/next");
