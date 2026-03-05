# path: oj/roadmap_data/stage_02.py

STAGE_2 = {
    "id": 2,
    "title": "⚙️ Giai đoạn 2: Cấu trúc dữ liệu cơ bản & hàm",
    "summary": "Biết cách lưu trữ, truy cập và xử lý dữ liệu có cấu trúc; chia nhỏ chương trình thành các hàm để dễ bảo trì và mở rộng.",
    "topics": [
        {
            "title": "2.1. Mảng 1D và 2D",
            "summary": "Hiểu cách khai báo, truy cập và duyệt mảng trong C++ và Python; làm việc với ma trận và tính toán cơ bản.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/2/topic/1/",
            "html_file": "roadmap_data/topics/stage02_topic01.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main() {
    int n;
    cin >> n;
    vector<int> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];
    long long sum = 0;
    for (int x : a) sum += x;
    cout << "Tong = " << sum;
    return 0;
}""",
            "sample_py": """n = int(input())
a = list(map(int, input().split()))
print("Tong =", sum(a))"""
        },
        {
            "title": "2.2. Chuỗi ký tự",
            "summary": "Làm việc với string: nhập chuỗi có dấu cách, nối chuỗi, đếm ký tự, đảo ngược chuỗi, và so sánh C++ – Python.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/2/topic/2/",
            "html_file": "roadmap_data/topics/stage02_topic02.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main() {
    string s;
    getline(cin, s);
    cout << "Chieu dai: " << s.size() << endl;
    reverse(s.begin(), s.end());
    cout << "Dao nguoc: " << s;
    return 0;
}""",
            "sample_py": """s = input()
print("Chieu dai:", len(s))
print("Dao nguoc:", s[::-1])"""
        },
        {
            "title": "2.3. Hàm và truyền tham trị / tham chiếu",
            "summary": "Học cách chia nhỏ chương trình thành hàm; hiểu truyền tham trị và tham chiếu; viết hàm kiểm tra, tính toán.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/2/topic/3/",
            "html_file": "roadmap_data/topics/stage02_topic03.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int cong(int a, int b) { return a + b; }
int main() {
    cout << cong(3, 5);
    return 0;
}""",
            "sample_py": """def cong(a, b):
    return a + b
print(cong(3, 5))"""
        },
        {
            "title": "2.4. Đọc và ghi file",
            "summary": "Làm quen với file I/O để xử lý dữ liệu thực tế, đọc dữ liệu từ file .INP và ghi kết quả ra file .OUT – giống bài thi HSG.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/2/topic/4/",
            "html_file": "roadmap_data/topics/stage02_topic04.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main() {
    ifstream fin("SUM.INP");
    ofstream fout("SUM.OUT");
    int a, b;
    fin >> a >> b;
    fout << (a + b);
    return 0;
}""",
            "sample_py": """fin = open("SUM.INP", "r")
fout = open("SUM.OUT", "w")
a, b = map(int, fin.read().split())
fout.write(str(a + b))
fin.close()
fout.close()"""
        },
    ],
}
