// PostConfig.js — offline local mirror overrides.
//
// Background / why this is the right hook:
//   - The live editor instance is an `App` (draw.io's App extends EditorUi).
//   - Ctrl/Cmd+S and the "Save" menu/toolbar action both resolve to
//     `App.prototype.saveFile` (NOT EditorUi.prototype.saveFile), because
//     App shadows it. So the override MUST be on App.prototype.saveFile.
//   - Out of the box, saveFile opens a FilenameDialog whose "Where" target
//     defaults to OneDrive (cloud). Offline, the cloud state-check
//     (`/microsoft?getState=1`) returns 404/timeouts and the save fails.
//
// Fix: make Save always download the diagram locally as a `.drawio` file,
// reusing draw.io's own device-download path (doSaveLocalFile, inherited
// from EditorUi), which builds a proper `<mxfile>` document via getFileData().
(function () {
  if (typeof App === "undefined" || !App.prototype || !App.prototype.saveFile) {
    window.__savePatched = "no-App";
    return;
  }
  window.__savePatched = "yes";

  var origAppSave = App.prototype.saveFile;

  App.prototype.saveFile = function (b, k) {
    try {
      var name = (this.editor && this.editor.filename) ||
                 this.defaultFilename || "drawing.drawio";
      if (!/\.drawio$/i.test(name)) {
        name = name.replace(/\.(xml|svg|html)$/i, "") + ".drawio";
      }
      var data = this.getFileData();
      if (typeof data !== "string" || data.indexOf("<mxfile") !== 0) {
        throw new Error("getFileData did not return an mxfile document");
      }
      this.doSaveLocalFile(data, name, "text/xml");
      if (typeof k === "function") { try { k(); } catch (e) {} }
      return;
    } catch (e) {
      if (typeof mxLog !== "undefined" && mxLog.debug) {
        mxLog.debug("Offline save failed, falling back: " + e);
      }
    }
    return origAppSave.apply(this, arguments);
  };
})();
