const fs = require("fs");
const pathModule = require("path");

if (process.platform !== "win32") {
  return;
}

function normalizeReadlinkError(path, error) {
  if (error?.code !== "EISDIR") {
    throw error;
  }

  try {
    const stat = fs.lstatSync(path);
    if (!stat.isSymbolicLink()) {
      const normalized = new Error(`EINVAL: invalid argument, readlink '${path}'`);
      normalized.code = "EINVAL";
      normalized.errno = -4071;
      normalized.path = path;
      normalized.syscall = "readlink";
      throw normalized;
    }
  } catch (statError) {
    if (statError?.code === "EINVAL") {
      throw statError;
    }
  }

  throw error;
}

function isReadlinkDirectoryError(error) {
  return error?.code === "EISDIR" && error?.syscall === "readlink";
}

function fallbackRealpath(path, error) {
  if (!isReadlinkDirectoryError(error)) {
    throw error;
  }

  return pathModule.resolve(path);
}

const readlinkSync = fs.readlinkSync;
fs.readlinkSync = function patchedReadlinkSync(path, options) {
  try {
    return readlinkSync.call(fs, path, options);
  } catch (error) {
    normalizeReadlinkError(path, error);
  }
};

const realpathSync = fs.realpathSync;
fs.realpathSync = function patchedRealpathSync(path, options) {
  try {
    return realpathSync.call(fs, path, options);
  } catch (error) {
    return fallbackRealpath(path, error);
  }
};

if (fs.realpathSync.native) {
  const nativeRealpathSync = fs.realpathSync.native;
  fs.realpathSync.native = function patchedNativeRealpathSync(path, options) {
    try {
      return nativeRealpathSync.call(fs.realpathSync, path, options);
    } catch (error) {
      return fallbackRealpath(path, error);
    }
  };
}

const readlink = fs.readlink;
fs.readlink = function patchedReadlink(path, options, callback) {
  const cb = typeof options === "function" ? options : callback;
  const opts = typeof options === "function" ? undefined : options;

  return readlink.call(fs, path, opts, (error, result) => {
    if (error) {
      try {
        normalizeReadlinkError(path, error);
      } catch (normalized) {
        cb(normalized);
        return;
      }
    }
    cb(null, result);
  });
};

const realpath = fs.realpath;
fs.realpath = function patchedRealpath(path, options, callback) {
  const cb = typeof options === "function" ? options : callback;
  const opts = typeof options === "function" ? undefined : options;

  return realpath.call(fs, path, opts, (error, result) => {
    if (error) {
      try {
        cb(null, fallbackRealpath(path, error));
        return;
      } catch (normalized) {
        cb(normalized);
        return;
      }
    }
    cb(null, result);
  });
};

if (fs.realpath.native) {
  const nativeRealpath = fs.realpath.native;
  fs.realpath.native = function patchedNativeRealpath(path, options, callback) {
    const cb = typeof options === "function" ? options : callback;
    const opts = typeof options === "function" ? undefined : options;

    return nativeRealpath.call(fs.realpath, path, opts, (error, result) => {
      if (error) {
        try {
          cb(null, fallbackRealpath(path, error));
          return;
        } catch (normalized) {
          cb(normalized);
          return;
        }
      }
      cb(null, result);
    });
  };
}

if (fs.promises?.readlink) {
  const promiseReadlink = fs.promises.readlink.bind(fs.promises);
  fs.promises.readlink = async function patchedPromiseReadlink(path, options) {
    try {
      return await promiseReadlink(path, options);
    } catch (error) {
      normalizeReadlinkError(path, error);
    }
  };
}

if (fs.promises?.realpath) {
  const promiseRealpath = fs.promises.realpath.bind(fs.promises);
  fs.promises.realpath = async function patchedPromiseRealpath(path, options) {
    try {
      return await promiseRealpath(path, options);
    } catch (error) {
      return fallbackRealpath(path, error);
    }
  };
}
