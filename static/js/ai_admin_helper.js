async function ai_generate_problem() {
    const res = await fetch("/problems/admin_ai_generate/");
    const d = await res.json();
    document.getElementById("id_statement").value = d.content;
    alert("✅ Đã sinh đề, kéo xuống xem!");
}

async function ai_generate_samples() {
    const text = document.getElementById("id_statement").value;
    const res = await fetch("/problems/admin_ai_samples/", {
        method: "POST",
        body: text
    });
    const d = await res.json();
    alert("✅ Sample đã sinh — scroll xuống Preview!");
}

async function ai_check_format() {
    const text = document.getElementById("id_statement").value;
    const res = await fetch("/problems/admin_ai_check/", {
        method: "POST",
        body: text
    });
    const d = await res.json();
    alert("📌 Format OK:\n\n" + d.msg);
}
