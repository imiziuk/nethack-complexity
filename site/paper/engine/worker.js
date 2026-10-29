/* Web Worker: loads Pyodide (pinned v0.26.4), installs the unmodified generator gen_on_instance.py and the glue
   driver.py into the Python file system, then answers {type:"run", instance} with the driver's JSON. Running
   Python here keeps the page responsive while the generator works. */
"use strict";
importScripts("https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js");
var driver = null;
async function init() {
  try {
    var t0 = Date.now();
    var py = await loadPyodide({ indexURL: "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/" });
    var src = await Promise.all(["gen_on_instance.py", "driver.py"].map(function (f) {
      return fetch(f, { cache: "no-cache" }).then(function (r) { if (!r.ok) throw new Error(f + ": HTTP " + r.status); return r.text(); });
    }));
    py.FS.mkdirTree("/engine");
    py.FS.writeFile("/engine/gen_on_instance.py", src[0]);
    py.FS.writeFile("/engine/engine_driver.py", src[1]);
    py.runPython("import sys; sys.path.insert(0, '/engine')");
    driver = py.pyimport("engine_driver");
    postMessage({ type: "ready", version: py.version, python: py.runPython("import sys; sys.version.split()[0]"),
                  ms: Date.now() - t0, genBytes: new TextEncoder().encode(src[0]).length });
  } catch (e) {
    postMessage({ type: "fatal", error: String(e && e.message || e) });
  }
}
var ready = init();
onmessage = async function (ev) {
  await ready;
  if (!driver) return;
  var m = ev.data;
  if (m.type !== "run") return;
  var t0 = Date.now();
  try {
    var out = driver.run(JSON.stringify(m.instance));
    postMessage({ type: "result", id: m.id, json: out, ms: Date.now() - t0 });
  } catch (e) {
    postMessage({ type: "result", id: m.id, json: JSON.stringify({ ok: false, kind: "PythonError", error: String(e && e.message || e) }), ms: Date.now() - t0 });
  }
};
