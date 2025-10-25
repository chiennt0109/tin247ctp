# path: oj/roadmap_data/stage_08.py

STAGE_8 = {
    "id": 8,
    "title": "🧱 Giai đoạn 8: Cấu trúc dữ liệu nâng cao",
    "summary": "Sử dụng các cấu trúc dữ liệu mạnh để tăng tốc độ xử lý và tối ưu lưu trữ.",
    "topics": [
        {
            "title": "8.1. Stack, Queue, Deque",
            "summary": "Các cấu trúc dữ liệu tuyến tính đặc biệt dùng để xử lý luồng dữ liệu.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/8/topic/1/",
            "html_file": "roadmap_data/topics/stage08_topic01.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main() {
    stack<int> st;
    queue<int> q;
    deque<int> dq;

    for (int i = 1; i <= 3; i++) {
        st.push(i);
        q.push(i);
        dq.push_back(i);
    }

    cout << "Stack top: " << st.top() << "\\n";
    cout << "Queue front: " << q.front() << "\\n";
    cout << "Deque back: " << dq.back() << "\\n";
}""",
            "sample_py": """from collections import deque

st = []
q = deque()
dq = deque()

for i in range(1, 4):
    st.append(i)
    q.append(i)
    dq.append(i)

print("Stack top:", st[-1])
print("Queue front:", q[0])
print("Deque back:", dq[-1])"""
        },
        {
            "title": "8.2. Linked List",
            "summary": "Lưu trữ dữ liệu linh hoạt, cho phép chèn và xóa nhanh hơn mảng.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/8/topic/2/",
            "html_file": "roadmap_data/topics/stage08_topic02.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
struct Node {
    int val;
    Node* next;
    Node(int v): val(v), next(NULL) {}
};
void print(Node* head){
    for(Node* p=head; p; p=p->next)
        cout<<p->val<<" ";
}
int main(){
    Node* head = new Node(1);
    head->next = new Node(2);
    head->next->next = new Node(3);
    print(head);
}""",
            "sample_py": """class Node:
    def __init__(self, val):
        self.val = val
        self.next = None

head = Node(1)
head.next = Node(2)
head.next.next = Node(3)

cur = head
while cur:
    print(cur.val, end=" ")
    cur = cur.next"""
        },
        {
            "title": "8.3. Hash Table & Priority Queue",
            "summary": "Truy cập dữ liệu siêu nhanh bằng Hash Map và cấu trúc Heap.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/8/topic/3/",
            "html_file": "roadmap_data/topics/stage08_topic03.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main(){
    unordered_map<string,int> mp;
    mp["apple"]=3; mp["banana"]=5; mp["orange"]=2;
    priority_queue<int> pq;
    pq.push(10); pq.push(5); pq.push(8);

    cout << "Hash apple = " << mp["apple"] << "\\n";
    cout << "Top of max-heap = " << pq.top() << "\\n";
}""",
            "sample_py": """import heapq

mp = {"apple": 3, "banana": 5, "orange": 2}
pq = []
for x in [10, 5, 8]:
    heapq.heappush(pq, -x)  # max-heap bằng âm số

print("Hash apple =", mp["apple"])
print("Top of max-heap =", -pq[0])"""
        },
    ],
}
