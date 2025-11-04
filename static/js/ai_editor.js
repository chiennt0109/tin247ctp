console.log("✅ AI Editor loaded");

async function callAI(endpoint, payload) {
    try {
        const res = await fetch(endpoint, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCSRF()
            },
            body: JSON.stringify(payload)
        });
        return await res.json();
    } catch (e) {
        alert("❌ Lỗi AI: " + e);
    }
}

function getCSRF() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

/* ✅ Tạo đề bài tự động */
async function aiGenerateStatement() {
    const title = document.querySelector("#id_title").value;
    if (!title) return alert("⚠️ Nhập Title trước!");

    const res = await callAI("/problems/ai_generate/", { title });
    if (!res) return;

    document.querySelector("#id_statement").value = res.statement || "";
    alert("✅ Đã tạo đề bài!");
}

/* ✅ Sửa LaTeX */
async function aiFixLatex() {
    const text = document.querySelector("#id_statement").value;
    const res = await callAI("/problems/ai_fix_latex/", { text });
    if (!res) return;

    document.querySelector("#id_statement").value = res.cleaned || text;
    alert("✅ LaTeX OK!");
}

/* ✅ Gợi ý tag / code / độ khó */
async function aiAutoTag() {
    const statement = document.querySelector("#id_statement").value;
    if (!statement) return alert("⚠️ Nhập đề trước!");

    const res = await callAI("/problems/ai_autotag/", { statement });
    if (!res) return;

    document.querySelector("#id_code").value = res.code || "";
    document.querySelector("#id_difficulty").value = res.difficulty || "Easy";

    alert(`✅ Gợi ý xong!\nTags: ${res.tags?.join(", ")}`);
}
