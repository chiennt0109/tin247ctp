// ✅ Gửi POST kèm CSRF
async function post(url, data = {}) {
    const csrf = document.querySelector("[name=csrfmiddlewaretoken]").value;
    const res = await fetch(url, {
        method: "POST",
        headers: {
            "X-CSRFToken": csrf,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams(data),
    });
    return await res.json();
}

// ✨ Sinh đề từ AI
async function ai_generate_problem() {
    const title = document.querySelector("#id_title").value || prompt("Nhập tên bài:");
    if (!title) return;

    const d = await post("/problems/admin_ai_generate/", { title });
    document.querySelector("#id_statement").value = d.statement;
    alert("✅ Đã sinh đề!");
}

// 🧪 Sinh sample input/output
async function ai_generate_samples() {
    const text = document.querySelector("#id_statement").value;
    const d = await post("/problems/admin_ai_samples/", { statement: text });
    alert("✅ Sample đã tạo. Kiểm tra preview bên dưới.");
}

// ✅ Check định dạng Markdown/Template
async function ai_check_format() {
    const text = document.querySelector("#id_statement").value;
    const d = await post("/problems/admin_ai_check/", { statement: text });
    alert("📌 Kết quả:\n\n" + d.message);
}

// 🏷️ Gợi ý Tag, mã bài, độ khó
async function ai_autotag() {
    const text = document.querySelector("#id_statement").value;
    const d = await post("/problems/admin_ai_autotag/", { statement: text });

    if (d.tags?.length) {
        alert("✅ Tags gợi ý: " + d.tags.join(", "));
        location.reload();
    } else {
        alert("ℹ️ Không nhận diện được tags.");
    }
}
