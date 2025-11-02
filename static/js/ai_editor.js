// path: static/js/ai_editor.js
async function postJSON(url, payload) {
  const csrftoken = getCookie('csrftoken');
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrftoken || "",
    },
    body: JSON.stringify(payload || {})
  });
  return res.json();
}

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
}

async function aiGenerateStatement() {
  const title = document.querySelector("#id_title")?.value || "";
  const statement = document.querySelector("#id_statement")?.value || "";
  try {
    const data = await postJSON("/admin/problems/problem/ai_generate/", { title, statement });
    if (data.error) return alert("❌ " + data.error);
    if (data.code) document.querySelector("#id_code").value = data.code;
    if (data.difficulty) document.querySelector("#id_difficulty").value = data.difficulty;

    // Gợi ý tags -> tick/append (nếu bạn dùng ManyToMany raw, hiển thị list)
    const tagSel = document.querySelector("#id_tags");
    if (tagSel && data.tags && Array.isArray(data.tags)) {
      // Chỉ set kết quả hiển thị; không tạo Tag mới ở đây
      document.getElementById("aiResult").innerHTML =
        `✅ <b>Mã:</b> ${data.code} — <b>Độ khó:</b> ${data.difficulty} — <b>Tags gợi ý:</b> ${data.tags.join(", ")}`;
    } else {
      document.getElementById("aiResult").innerHTML =
        `✅ <b>Mã:</b> ${data.code} — <b>Độ khó:</b> ${data.difficulty}`;
    }
  } catch (e) {
    alert("❌ AI lỗi: " + e.message);
  }
}

async function aiFixLatex() {
  try {
    const data = await postJSON("/admin/problems/problem/ai_check/", {});
    alert(data?.message || "Đã kiểm tra LaTeX/Markdown.");
  } catch (e) {
    alert("❌ Lỗi: " + e.message);
  }
}

async function aiAutoTag() {
  try {
    const data = await postJSON("/admin/problems/problem/ai_autotag/", {});
    if (data && Array.isArray(data.tags)) {
      document.getElementById("aiResult").innerHTML =
        `🏷️ Gợi ý tags: ${data.tags.join(", ")}`;
    } else {
      alert("Không nhận được gợi ý tags.");
    }
  } catch (e) {
    alert("❌ Lỗi: " + e.message);
  }
}
