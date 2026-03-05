document.addEventListener("DOMContentLoaded", function () {
    const textarea = document.getElementById("id_statement");
    const preview = document.getElementById("preview-box");

    function render() {
        if (!textarea || !preview) return;
        let html = marked.parse(textarea.value);
        preview.innerHTML = html;

        if (window.renderMathInElement) {
            renderMathInElement(preview, {
                delimiters: [
                    {left: "$$", right: "$$", display: true},
                    {left: "$", right: "$", display: false},
                ]
            });
        }
    }

    textarea?.addEventListener("input", render);
    render();
});
