# path: oj/roadmap_data/stage_07.py

STAGE_7 = {
    "id": 7,
    "title": "🎯 Giai đoạn 7: Quay lui & nhánh cận (Backtracking)",
    "summary": "Duyệt toàn bộ không gian nghiệm và cắt tỉa nhánh không cần thiết để tối ưu thời gian.",
    "topics": [
        {
            "title": "7.1. Sinh tổ hợp & hoán vị",
            "summary": "Viết chương trình sinh ra mọi tổ hợp hoặc hoán vị có thể có.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/7/topic/1/",
            "html_file": "roadmap_data/topics/stage07_topic01.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> used;
vector<int> cur;

void backtrack() {
    if ((int)cur.size() == n) {
        for (int x : cur) cout << x << " ";
        cout << "\\n";
        return;
    }
    for (int val = 1; val <= n; val++) {
        if (!used[val]) {
            used[val] = 1;
            cur.push_back(val);
            backtrack();
            cur.pop_back();
            used[val] = 0;
        }
    }
}

int main() {
    cin >> n;
    used.assign(n+1, 0);
    backtrack();
}""",
            "sample_py": """n = int(input())
used = [False] * (n + 1)
cur = []

def backtrack():
    if len(cur) == n:
        print(*cur)
        return
    for val in range(1, n+1):
        if not used[val]:
            used[val] = True
            cur.append(val)
            backtrack()
            cur.pop()
            used[val] = False

backtrack()"""
        },
        {
            "title": "7.2. N-Queens",
            "summary": "Bài toán đặt hậu kinh điển giúp hiểu sâu về quay lui và kiểm tra ràng buộc.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/7/topic/2/",
            "html_file": "roadmap_data/topics/stage07_topic02.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> col, diag1, diag2, pos;
int solutions = 0;

void backtrack(int row) {
    if (row == n) {
        solutions++;
        for (int r = 0; r < n; r++) {
            for (int c = 0; c < n; c++) {
                cout << (pos[r] == c ? "Q" : ".");
            }
            cout << "\\n";
        }
        cout << "\\n";
        return;
    }
    for (int c = 0; c < n; c++) {
        if (!col[c] && !diag1[row+c] && !diag2[row-c+n-1]) {
            col[c] = diag1[row+c] = diag2[row-c+n-1] = 1;
            pos[row] = c;
            backtrack(row+1);
            col[c] = diag1[row+c] = diag2[row-c+n-1] = 0;
        }
    }
}

int main() {
    cin >> n;
    col.assign(n,0);
    diag1.assign(2*n,0);
    diag2.assign(2*n,0);
    pos.assign(n,-1);
    backtrack(0);
    cerr << "Total solutions: " << solutions << "\\n";
}""",
            "sample_py": """n = int(input())
col = [False]*n
diag1 = [False]*(2*n)
diag2 = [False]*(2*n)
pos = [-1]*n
solutions = 0

def backtrack(row):
    global solutions
    if row == n:
        solutions += 1
        for r in range(n):
            line = "".join("Q" if pos[r] == c else "." for c in range(n))
            print(line)
        print()
        return
    for c in range(n):
        if not col[c] and not diag1[row+c] and not diag2[row-c+n-1]:
            col[c] = diag1[row+c] = diag2[row-c+n-1] = True
            pos[row] = c
            backtrack(row+1)
            col[c] = diag1[row+c] = diag2[row-c+n-1] = False

backtrack(0)
print("Total solutions:", solutions)"""
        },
        {
            "title": "7.3. Sudoku Solver",
            "summary": "Ứng dụng quay lui để giải Sudoku chuẩn xác và hiệu quả.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/7/topic/3/",
            "html_file": "roadmap_data/topics/stage07_topic03.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;

int board[9][9];

bool ok(int r, int c, int val){
    for(int i=0;i<9;i++){
        if(board[r][i]==val) return false;
        if(board[i][c]==val) return false;
    }
    int br=(r/3)*3, bc=(c/3)*3;
    for(int i=0;i<3;i++)
        for(int j=0;j<3;j++)
            if(board[br+i][bc+j]==val) return false;
    return true;
}

bool solve(){
    for(int r=0;r<9;r++){
        for(int c=0;c<9;c++){
            if(board[r][c]==0){
                for(int v=1;v<=9;v++){
                    if(ok(r,c,v)){
                        board[r][c]=v;
                        if(solve()) return true;
                        board[r][c]=0;
                    }
                }
                return false;
            }
        }
    }
    return true;
}

int main(){
    for(int i=0;i<9;i++)
        for(int j=0;j<9;j++)
            cin>>board[i][j];
    solve();
    for(int i=0;i<9;i++){
        for(int j=0;j<9;j++){
            cout<<board[i][j]<<" ";
        }
        cout<<"\\n";
    }
}""",
            "sample_py": """board = [list(map(int, input().split())) for _ in range(9)]

def ok(r, c, val):
    # check row & col
    for i in range(9):
        if board[r][i] == val: return False
        if board[i][c] == val: return False
    # check 3x3 box
    br, bc = (r//3)*3, (c//3)*3
    for i in range(3):
        for j in range(3):
            if board[br+i][bc+j] == val:
                return False
    return True

def solve():
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                for v in range(1, 10):
                    if ok(r,c,v):
                        board[r][c] = v
                        if solve():
                            return True
                        board[r][c] = 0
                return False
    return True

solve()
for row in board:
    print(*row)"""
        },
    ],
}
