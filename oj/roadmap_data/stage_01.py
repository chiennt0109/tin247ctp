STAGE_1 = {
    "id": 1,
    "title": "🧩 Giai đoạn 1: Làm quen với thuật toán và cấu trúc cơ bản",
    "summary": "Khởi đầu hành trình với biến, vòng lặp, và tư duy thuật toán đơn giản.",
    "topics": [
        # =====================================================
        # 1.1 BIẾN, KIỂU DỮ LIỆU VÀ NHẬP XUẤT
        # =====================================================
        {
            "title": "1.1. Biến, kiểu dữ liệu và nhập xuất",
            "summary": "Hiểu cách khai báo biến, nhập và xuất dữ liệu trong C++ và Python.",
            "more_url": "/stages/1/topic/1/",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main() {
    int a, b;
    cin >> a >> b;
    cout << a + b << endl;
    return 0;
}""",
            "sample_py": """a, b = map(int, input().split())
print(a + b)""",
            "detail": """
<h2>🎯 Mục tiêu bài học</h2>
<ul>
  <li>Hiểu <b>biến</b> là gì và cách khai báo biến.</li>
  <li>Biết <b>nhập dữ liệu từ bàn phím</b> và <b>in kết quả ra màn hình</b>.</li>
  <li>Thực hành viết chương trình đầu tiên: <code>Tính tổng hai số</code>.</li>
</ul>

<h2>📘 1. Cấu trúc cơ bản của chương trình C++</h2>
<pre><code>#include &lt;bits/stdc++.h&gt;
using namespace std;

int main() {
    // Code sẽ viết ở đây
    return 0;
}</code></pre>

<p>Hãy ghi nhớ: 4 dòng trên là “khung xương” của mọi chương trình C++.</p>

<h2>🐍 2. Cấu trúc chương trình Python</h2>
<pre><code># Python không cần include hay main()
print("Xin chao!")</code></pre>

<p>Python đơn giản hơn: chỉ cần viết lệnh là chạy được.</p>

<h2>🧮 3. Biến là gì?</h2>
<p><b>Biến</b> giống như chiếc hộp để lưu trữ giá trị.</p>

<table class="table table-bordered text-sm">
<thead><tr><th>Ngôn ngữ</th><th>Cú pháp</th><th>Ví dụ</th></tr></thead>
<tbody>
<tr><td>C++</td><td><code>int a = 5;</code></td><td>Khai báo biến a kiểu số nguyên</td></tr>
<tr><td>Python</td><td><code>a = 5</code></td><td>Không cần ghi kiểu dữ liệu</td></tr>
</tbody></table>

<h2>⌨️ 4. Nhập và xuất dữ liệu</h2>
<table class="table table-bordered text-sm">
<thead><tr><th>C++</th><th>Python</th></tr></thead>
<tbody>
<tr><td><pre><code>int a, b;
cin >> a >> b;
cout << a + b;</code></pre></td>
<td><pre><code>a, b = map(int, input().split())
print(a + b)</code></pre></td></tr>
</tbody></table>

<h2>🧑‍🏫 5. Thử ngay</h2>
<p>Bên khung lập trình, hãy:</p>
<ol>
  <li>Chọn ngôn ngữ C++ hoặc Python.</li>
  <li>Dán code ví dụ vào.</li>
  <li>Nhập hai số như “5 7”.</li>
  <li>Xem kết quả xuất ra.</li>
</ol>

<h2>🧩 Bài tập luyện tập</h2>
<ol>
  <li>Nhập 2 số nguyên, in ra tổng, hiệu, tích, thương.</li>
  <li>Nhập tên và tuổi, in ra: <code>Xin chào [tên], bạn [tuổi] tuổi!</code></li>
  <li>Nhập n, tính tổng các số từ 1 đến n.</li>
</ol>
            """,
        },

        # =====================================================
        # 1.2 CẤU TRÚC ĐIỀU KIỆN IF / ELSE
        # =====================================================
        {
            "title": "1.2. Cấu trúc điều kiện (if / else)",
            "summary": "Phân nhánh quyết định trong chương trình – nền tảng cho mọi thuật toán phức tạp.",
            "more_url": "/stages/1/topic/2/",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main() {
    int n;
    cin >> n;
    if (n % 2 == 0)
        cout << "Even";
    else
        cout << "Odd";
    return 0;
}""",
            "sample_py": """n = int(input())
print("Even" if n % 2 == 0 else "Odd")""",
            "detail": """
<h2>🎯 Mục tiêu bài học</h2>
<ul>
  <li>Hiểu được cấu trúc rẽ nhánh: <code>if</code>, <code>else</code>.</li>
  <li>Biết cách so sánh, kiểm tra điều kiện trong chương trình.</li>
</ul>

<h2>📘 1. Cấu trúc điều kiện trong C++</h2>
<pre><code>if (điều_kiện) {
    // Nếu điều kiện đúng, thực hiện khối lệnh này
} else {
    // Nếu sai, thực hiện khối lệnh khác
}</code></pre>

<h2>🐍 2. Trong Python</h2>
<pre><code>if điều_kiện:
    # Lệnh khi đúng
else:
    # Lệnh khi sai</code></pre>

<h2>🧩 Ví dụ: Kiểm tra số chẵn hay lẻ</h2>
<table class="table table-bordered text-sm">
<thead><tr><th>C++</th><th>Python</th></tr></thead>
<tbody><tr><td>
<pre><code>#include &lt;bits/stdc++.h&gt;
using namespace std;
int main() {
    int n;
    cin >> n;
    if (n % 2 == 0)
        cout << "Even";
    else
        cout << "Odd";
}</code></pre></td>
<td>
<pre><code>n = int(input())
if n % 2 == 0:
    print("Even")
else:
    print("Odd")</code></pre></td></tr></tbody></table>

<h2>🎯 Ứng dụng mở rộng</h2>
<ul>
  <li>Kiểm tra tuổi hợp lệ.</li>
  <li>Kiểm tra học sinh có đậu hay không (điểm ≥ 5).</li>
  <li>So sánh hai số và in ra số lớn hơn.</li>
</ul>

<h2>💡 Bài tập</h2>
<ol>
  <li>Nhập một số nguyên, cho biết là dương, âm hay bằng 0.</li>
  <li>Nhập điểm, in ra kết quả: “Đậu” hoặc “Rớt”.</li>
  <li>Nhập 3 số, in ra số lớn nhất.</li>
</ol>
            """,
        },

        # =====================================================
        # 1.3 VÒNG LẶP FOR / WHILE
        # =====================================================
        {
            "title": "1.3. Vòng lặp for / while",
            "summary": "Tự động hoá thao tác lặp, xử lý dãy số, tính tổng, đếm, kiểm tra điều kiện lặp.",
            "more_url": "/stages/1/topic/3/",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main() {
    int n, sum = 0;
    cin >> n;
    for (int i = 1; i <= n; i++)
        sum += i;
    cout << sum;
    return 0;
}""",
            "sample_py": """n = int(input())
print(sum(range(1, n + 1)))""",
            "detail": """
<h2>🎯 Mục tiêu bài học</h2>
<ul>
  <li>Hiểu khái niệm <b>vòng lặp</b> – lặp lại một công việc nhiều lần.</li>
  <li>Phân biệt giữa <code>for</code> và <code>while</code>.</li>
  <li>Thực hành tính tổng, đếm, in dãy số.</li>
</ul>

<h2>📘 1. Vòng lặp for trong C++</h2>
<pre><code>for (int i = 1; i <= n; i++) {
    // khối lệnh lặp
}</code></pre>

<h2>🐍 Trong Python</h2>
<pre><code>for i in range(1, n + 1):
    # khối lệnh lặp
</code></pre>

<h2>🧩 Ví dụ: Tính tổng từ 1 đến n</h2>
<table class="table table-bordered text-sm">
<thead><tr><th>C++</th><th>Python</th></tr></thead>
<tbody><tr><td>
<pre><code>int n, sum = 0;
cin >> n;
for (int i = 1; i <= n; i++)
    sum += i;
cout << sum;</code></pre></td>
<td>
<pre><code>n = int(input())
total = 0
for i in range(1, n + 1):
    total += i
print(total)</code></pre></td></tr></tbody></table>

<h2>🔁 2. Vòng lặp while</h2>
<table class="table table-bordered text-sm">
<thead><tr><th>C++</th><th>Python</th></tr></thead>
<tbody><tr><td>
<pre><code>int i = 1;
while (i <= n) {
    cout << i << " ";
    i++;
}</code></pre></td>
<td>
<pre><code>i = 1
while i <= n:
    print(i, end=" ")
    i += 1</code></pre></td></tr></tbody></table>

<h2>💡 Bài tập luyện tập</h2>
<ol>
  <li>Nhập n, in ra dãy 1 → n.</li>
  <li>Tính tổng các số chẵn từ 1 → n.</li>
  <li>Tính giai thừa n! (ví dụ 5! = 1×2×3×4×5).</li>
</ol>

<h2>🧠 Thử thách mở rộng</h2>
<p>Hãy thử dùng <code>while</code> thay cho <code>for</code> để làm lại các bài trên.</p>
            """,
        },
    ],
}
