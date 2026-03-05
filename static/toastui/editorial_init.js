document.addEventListener("DOMContentLoaded", function () {

    const textarea = document.querySelector("textarea[name='content']");
    if (!textarea) {
        console.warn("Không tìm th?y textarea content");
        return;
    }

    textarea.style.display = "none";

    const editorDiv = document.createElement("div");
    textarea.parentNode.insertBefore(editorDiv, textarea);

    const editor = new toastui.Editor({
        el: editorDiv,
        height: "600px",
        initialEditType: "markdown",
        previewStyle: "vertical",
        usageStatistics: false,
        initialValue: textarea.value || "",
    });

    textarea.closest("form").addEventListener("submit", () => {
        textarea.value = editor.getMarkdown();
    });
});
