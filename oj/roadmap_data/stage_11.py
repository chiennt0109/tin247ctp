# path: oj/roadmap_data/stage_11.py

STAGE_11 = {
    "id": 11,
    "title": "🌲 Giai đoạn 11: Cây & cấu trúc đặc biệt",
    "summary": "Hiểu và sử dụng các loại cây để truy vấn & cập nhật dữ liệu nhanh chóng.",
    "topics": [
        {
            "title": "11.1. Cây nhị phân & Binary Search Tree (BST)",
            "summary": "Giới thiệu khái niệm cây, các phép duyệt cơ bản và nguyên lý tìm kiếm của BST.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/11/topic/1/",
            "html_file": "roadmap_data/topics/stage11_topic01.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
struct Node {
    int val;
    Node *left, *right;
    Node(int v): val(v), left(NULL), right(NULL) {}
};
void insert(Node*& root, int v) {
    if(!root) root = new Node(v);
    else if(v < root->val) insert(root->left, v);
    else insert(root->right, v);
}
void inorder(Node* root){
    if(!root) return;
    inorder(root->left);
    cout<<root->val<<" ";
    inorder(root->right);
}
int main(){
    Node* root=NULL;
    for(int x:{5,3,7,2,4,6,8}) insert(root,x);
    inorder(root);
}""",
            "sample_py": """class Node:
    def __init__(self,val):
        self.val=val;self.left=None;self.right=None
def insert(root,val):
    if not root: return Node(val)
    if val<root.val: root.left=insert(root.left,val)
    else: root.right=insert(root.right,val)
    return root
def inorder(root):
    if not root: return
    inorder(root.left);print(root.val,end=' ');inorder(root.right)
root=None
for x in [5,3,7,2,4,6,8]: root=insert(root,x)
inorder(root)"""
        },
        {
            "title": "11.2. Cây cân bằng (AVL, Red-Black Tree)",
            "summary": "Cách duy trì cân bằng để đảm bảo độ phức tạp O(log n) cho mọi thao tác.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/11/topic/2/",
            "html_file": "roadmap_data/topics/stage11_topic02.html",
            "sample_cpp": """// Minh hoạ AVL cơ bản
#include <bits/stdc++.h>
using namespace std;
struct Node{
    int val,height;
    Node *left,*right;
    Node(int v):val(v),height(1),left(NULL),right(NULL){}
};
int h(Node* n){return n?n->height:0;}
Node* rotateRight(Node* y){
    Node* x=y->left; Node* T2=x->right;
    x->right=y; y->left=T2;
    y->height=max(h(y->left),h(y->right))+1;
    x->height=max(h(x->left),h(x->right))+1;
    return x;
}
Node* rotateLeft(Node* x){
    Node* y=x->right; Node* T2=y->left;
    y->left=x; x->right=T2;
    x->height=max(h(x->left),h(x->right))+1;
    y->height=max(h(y->left),h(y->right))+1;
    return y;
}
int getBalance(Node* n){return n? h(n->left)-h(n->right):0;}
Node* insert(Node* node,int val){
    if(!node) return new Node(val);
    if(val<node->val) node->left=insert(node->left,val);
    else if(val>node->val) node->right=insert(node->right,val);
    else return node;
    node->height=max(h(node->left),h(node->right))+1;
    int bal=getBalance(node);
    if(bal>1 && val<node->left->val) return rotateRight(node);
    if(bal<-1 && val>node->right->val) return rotateLeft(node);
    if(bal>1 && val>node->left->val){ node->left=rotateLeft(node->left); return rotateRight(node);}
    if(bal<-1 && val<node->right->val){ node->right=rotateRight(node->right); return rotateLeft(node);}
    return node;
}
void inorder(Node* r){if(!r)return; inorder(r->left); cout<<r->val<<" "; inorder(r->right);}
int main(){
    Node* root=NULL;
    for(int x:{10,20,30,40,50,25}) root=insert(root,x);
    inorder(root);
}""",
            "sample_py": """# AVL cơ bản (rút gọn)
class Node:
    def __init__(self,val):
        self.val=val;self.left=None;self.right=None;self.h=1
def h(n): return n.h if n else 0
def rotR(y):
    x=y.left;T2=x.right;x.right=y;y.left=T2
    y.h=max(h(y.left),h(y.right))+1
    x.h=max(h(x.left),h(x.right))+1
    return x
def rotL(x):
    y=x.right;T2=y.left;y.left=x;x.right=T2
    x.h=max(h(x.left),h(x.right))+1
    y.h=max(h(y.left),h(y.right))+1
    return y
def bal(n): return h(n.left)-h(n.right) if n else 0
def insert(node,v):
    if not node: return Node(v)
    if v<node.val: node.left=insert(node.left,v)
    elif v>node.val: node.right=insert(node.right,v)
    else: return node
    node.h=max(h(node.left),h(node.right))+1
    b=bal(node)
    if b>1 and v<node.left.val: return rotR(node)
    if b<-1 and v>node.right.val: return rotL(node)
    if b>1 and v>node.left.val:
        node.left=rotL(node.left);return rotR(node)
    if b<-1 and v<node.right.val:
        node.right=rotR(node.right);return rotL(node)
    return node
def inorder(r): 
    if not r:return
    inorder(r.left);print(r.val,end=' ');inorder(r.right)
root=None
for x in [10,20,30,40,50,25]: root=insert(root,x)
inorder(root)"""
        },
        {
            "title": "11.3. Segment Tree & Fenwick Tree (BIT)",
            "summary": "Các cấu trúc dữ liệu mạnh để truy vấn tổng, cực trị, hoặc cập nhật nhanh.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/11/topic/3/",
            "html_file": "roadmap_data/topics/stage11_topic03.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
struct SegTree {
    int n; vector<long long> st;
    SegTree(int n):n(n){st.assign(4*n,0);}
    void update(int id,int l,int r,int pos,long long val){
        if(l==r){st[id]=val;return;}
        int mid=(l+r)/2;
        if(pos<=mid) update(id*2,l,mid,pos,val);
        else update(id*2+1,mid+1,r,pos,val);
        st[id]=st[id*2]+st[id*2+1];
    }
    long long query(int id,int l,int r,int u,int v){
        if(v<l||r<u) return 0;
        if(u<=l&&r<=v) return st[id];
        int mid=(l+r)/2;
        return query(id*2,l,mid,u,v)+query(id*2+1,mid+1,r,u,v);
    }
};
int main(){
    int n=5; SegTree seg(n);
    for(int i=1;i<=n;i++) seg.update(1,1,n,i,i);
    cout<<seg.query(1,1,n,2,4);
}""",
            "sample_py": """class Fenwick:
    def __init__(self,n):
        self.n=n;self.bit=[0]*(n+1)
    def update(self,i,val):
        while i<=self.n:
            self.bit[i]+=val
            i+=i&-i
    def query(self,i):
        s=0
        while i>0:
            s+=self.bit[i]
            i-=i&-i
        return s
fw=Fenwick(5)
for i in range(1,6): fw.update(i,i)
print(fw.query(4)-fw.query(1))"""
        },
        {
            "title": "11.4. Trie & Union-Find",
            "summary": "Trie dùng để xử lý chuỗi, Union-Find dùng để xác định nhóm liên thông.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/11/topic/4/",
            "html_file": "roadmap_data/topics/stage11_topic04.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
struct Trie{
    map<char,Trie*> child;
    bool end=false;
    void insert(string s){
        Trie* node=this;
        for(char c:s){
            if(!node->child[c]) node->child[c]=new Trie();
            node=node->child[c];
        }
        node->end=true;
    }
    bool search(string s){
        Trie* node=this;
        for(char c:s){
            if(!node->child[c]) return false;
            node=node->child[c];
        }
        return node->end;
    }
};
struct DSU{
    vector<int> p;
    DSU(int n){p.resize(n+1);iota(p.begin(),p.end(),0);}
    int find(int x){return x==p[x]?x:p[x]=find(p[x]);}
    void unite(int a,int b){a=find(a);b=find(b);if(a!=b)p[b]=a;}
};
int main(){
    Trie root;
    root.insert("cat"); root.insert("car");
    cout<<root.search("car")<<"\\n";
    DSU d(5); d.unite(1,2); cout<<(d.find(1)==d.find(2));
}""",
            "sample_py": """class Trie:
    def __init__(self):
        self.child={};self.end=False
    def insert(self,s):
        node=self
        for c in s:
            if c not in node.child:
                node.child[c]=Trie()
            node=node.child[c]
        node.end=True
    def search(self,s):
        node=self
        for c in s:
            if c not in node.child: return False
            node=node.child[c]
        return node.end
root=Trie()
for w in ["cat","car"]: root.insert(w)
print(root.search("car"))

class DSU:
    def __init__(self,n):
        self.p=list(range(n+1))
    def find(self,x):
        if self.p[x]!=x: self.p[x]=self.find(self.p[x])
        return self.p[x]
    def unite(self,a,b):
        ra,rb=self.find(a),self.find(b)
        if ra!=rb: self.p[rb]=ra
dsu=DSU(5)
dsu.unite(1,2)
print(dsu.find(1)==dsu.find(2))"""
        },
    ],
}
