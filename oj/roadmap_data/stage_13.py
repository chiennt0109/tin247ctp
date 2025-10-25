# path: oj/roadmap_data/stage_13.py

STAGE_13 = {
    "id": 13,
    "title": "🔤 Giai đoạn 13: Chuỗi và xử lý văn bản",
    "summary": "Học các thuật toán xử lý chuỗi mạnh mẽ – từ tìm kiếm, so khớp mẫu đến kiểm tra đối xứng.",
    "topics": [
        {
            "title": "13.1. KMP & Z-algorithm",
            "summary": "Thuật toán tìm mẫu trong chuỗi nhanh hơn gấp nhiều lần so với tìm kiếm tuyến tính.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/13/topic/1/",
            "html_file": "roadmap_data/topics/stage13_topic01.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
// KMP: tìm mẫu trong chuỗi
vector<int> buildLPS(string p){
    int n=p.size(); vector<int> lps(n);
    for(int i=1,len=0;i<n;){
        if(p[i]==p[len]) lps[i++]=++len;
        else if(len) len=lps[len-1];
        else lps[i++]=0;
    }
    return lps;
}
void KMP(string t,string p){
    vector<int> lps=buildLPS(p);
    for(int i=0,j=0;i<t.size();){
        if(t[i]==p[j]){i++;j++;}
        if(j==p.size()){cout<<"Found at "<<i-j<<"\\n"; j=lps[j-1];}
        else if(i<t.size() && t[i]!=p[j])
            j?j=lps[j-1]:i++;
}
}
int main(){
    string t="ababcababcabc", p="ababc";
    KMP(t,p);
}""",
            "sample_py": """def build_lps(p):
    n=len(p);lps=[0]*n;length=0;i=1
    while i<n:
        if p[i]==p[length]:
            length+=1;lps[i]=length;i+=1
        else:
            if length: length=lps[length-1]
            else: lps[i]=0;i+=1
    return lps
def kmp(t,p):
    lps=build_lps(p)
    i=j=0
    while i<len(t):
        if t[i]==p[j]:
            i+=1;j+=1
        if j==len(p):
            print("Found at",i-j)
            j=lps[j-1]
        elif i<len(t) and t[i]!=p[j]:
            if j: j=lps[j-1]
            else: i+=1
kmp("ababcababcabc","ababc")"""
        },
        {
            "title": "13.2. Rolling Hash",
            "summary": "Tăng tốc độ tìm kiếm và so khớp chuỗi bằng cách mã hoá chuỗi thành giá trị hash.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/13/topic/2/",
            "html_file": "roadmap_data/topics/stage13_topic02.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
const long long BASE=131,MOD=1e9+7;
vector<long long> pw,hashP;
void buildHash(string s){
    int n=s.size();
    pw.assign(n+1,1); hashP.assign(n+1,0);
    for(int i=1;i<=n;i++){
        pw[i]=pw[i-1]*BASE%MOD;
        hashP[i]=(hashP[i-1]*BASE+s[i-1])%MOD;
    }
}
long long getHash(int l,int r){ // 1-based
    return (hashP[r]-hashP[l-1]*pw[r-l+1]%MOD+MOD)%MOD;
}
int main(){
    string s="abracadabra";
    buildHash(s);
    cout<<getHash(1,3)<<" "<<getHash(8,10);
}""",
            "sample_py": """BASE=131;MOD=10**9+7
def build_hash(s):
    n=len(s)
    pw=[1]*(n+1);h=[0]*(n+1)
    for i in range(1,n+1):
        pw[i]=pw[i-1]*BASE%MOD
        h[i]=(h[i-1]*BASE+ord(s[i-1]))%MOD
    return pw,h
def get_hash(l,r,pw,h):
    return (h[r]-h[l-1]*pw[r-l+1]%MOD+MOD)%MOD
s="abracadabra"
pw,h=build_hash(s)
print(get_hash(1,3,pw,h),get_hash(8,10,pw,h))"""
        },
        {
            "title": "13.3. Palindrome & Substring",
            "summary": "Nhận diện và xử lý các chuỗi đối xứng, tìm chuỗi con có tính chất đặc biệt.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/13/topic/3/",
            "html_file": "roadmap_data/topics/stage13_topic03.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
bool isPal(string s){
    for(int i=0,j=s.size()-1;i<j;i++,j--)
        if(s[i]!=s[j]) return false;
    return true;
}
string longestPal(string s){
    int n=s.size(),start=0,len=1;
    for(int i=0;i<n;i++){
        int l=i,r=i;
        while(l>=0 && r<n && s[l]==s[r]){
            if(r-l+1>len){len=r-l+1;start=l;}
            l--;r++;
        }
        l=i;r=i+1;
        while(l>=0 && r<n && s[l]==s[r]){
            if(r-l+1>len){len=r-l+1;start=l;}
            l--;r++;
        }
    }
    return s.substr(start,len);
}
int main(){
    string s="babad";
    cout<<longestPal(s);
}""",
            "sample_py": """def is_pal(s):
    return s==s[::-1]
def longest_pal(s):
    res=""
    for i in range(len(s)):
        for j in range(i,len(s)):
            t=s[i:j+1]
            if len(t)>len(res) and t==t[::-1]:
                res=t
    return res
print(longest_pal("babad"))"""
        },
        {
            "title": "13.4. Pattern Matching nâng cao",
            "summary": "Ứng dụng thực tế trong kiểm tra chính tả, tìm kiếm văn bản và nhận dạng mẫu.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/13/topic/4/",
            "html_file": "roadmap_data/topics/stage13_topic04.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
// Rabin-Karp (pattern hashing)
const long long BASE=257,MOD=1e9+9;
vector<long long> pw,h;
void buildHash(string s){
    int n=s.size();
    pw.assign(n+1,1);h.assign(n+1,0);
    for(int i=1;i<=n;i++){
        pw[i]=pw[i-1]*BASE%MOD;
        h[i]=(h[i-1]*BASE+s[i-1])%MOD;
    }
}
long long getHash(int l,int r){
    return (h[r]-h[l-1]*pw[r-l+1]%MOD+MOD)%MOD;
}
int main(){
    string text="hellotherehello", pat="hello";
    buildHash(text);
    long long hashP=0;
    for(char c:pat) hashP=(hashP*BASE+c)%MOD;
    int n=text.size(),m=pat.size();
    for(int i=1;i+m-1<=n;i++){
        if(getHash(i,i+m-1)==hashP)
            cout<<"Match at position "<<i-1<<"\\n";
    }
}""",
            "sample_py": """BASE=257;MOD=10**9+9
def build_hash(s):
    n=len(s)
    pw=[1]*(n+1);h=[0]*(n+1)
    for i in range(1,n+1):
        pw[i]=pw[i-1]*BASE%MOD
        h[i]=(h[i-1]*BASE+ord(s[i-1]))%MOD
    return pw,h
def get_hash(l,r,pw,h):
    return (h[r]-h[l-1]*pw[r-l+1]%MOD+MOD)%MOD
text="hellotherehello";pat="hello"
pw,h=build_hash(text)
hashP=0
for c in pat: hashP=(hashP*BASE+ord(c))%MOD
for i in range(1,len(text)-len(pat)+2):
    if get_hash(i,i+len(pat)-1,pw,h)==hashP:
        print("Match at",i-1)"""
        },
    ],
}
