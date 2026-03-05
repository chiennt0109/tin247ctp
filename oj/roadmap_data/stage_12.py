# path: oj/roadmap_data/stage_12.py

STAGE_12 = {
    "id": 12,
    "title": "📐 Giai đoạn 12: Lý thuyết số và toán ứng dụng",
    "summary": "Ứng dụng các công cụ toán học trong lập trình để xử lý bài toán chia hết, modulo và tổ hợp.",
    "topics": [
        {
            "title": "12.1. GCD, LCM & Euclid mở rộng",
            "summary": "Tìm ước chung lớn nhất, bội chung nhỏ nhất và cách mở rộng Euclid để tìm nghiệm.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/12/topic/1/",
            "html_file": "roadmap_data/topics/stage12_topic01.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
long long gcd_ll(long long a,long long b){
    return b==0?a:gcd_ll(b,a%b);
}
long long lcm_ll(long long a,long long b){
    return a/gcd_ll(a,b)*b;
}
long long extgcd(long long a,long long b,long long &x,long long &y){
    if(b==0){x=1;y=0;return a;}
    long long x1,y1;
    long long g=extgcd(b,a%b,x1,y1);
    x=y1;
    y=x1-(a/b)*y1;
    return g;
}
int main(){
    long long a,b;cin>>a>>b;
    cout<<"gcd="<<gcd_ll(a,b)<<" lcm="<<lcm_ll(a,b)<<"\\n";
    long long x,y;
    long long g=extgcd(a,b,x,y);
    cout<<"ax+by=g => "<<a<<"*"<<x<<" + "<<b<<"*"<<y<<" = "<<g<<"\\n";
}""",
            "sample_py": """def gcd(a,b):
    while b:
        a,b=b,a%b
    return a
def lcm(a,b):
    return a//gcd(a,b)*b
def extgcd(a,b):
    if b==0:
        return a,1,0
    g,x1,y1=extgcd(b,a%b)
    x=y1
    y=x1-(a//b)*y1
    return g,x,y
a,b=map(int,input().split())
g,x,y=extgcd(a,b)
print("gcd=",g,"lcm=",lcm(a,b))
print("ax+by=g =>",a,"*",x,"+",b,"*",y,"=",g)"""
        },
        {
            "title": "12.2. Modulo & nghịch đảo",
            "summary": "Áp dụng modulo trong bài toán lớn và hiểu cơ chế nghịch đảo trong toán học lập trình.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/12/topic/2/",
            "html_file": "roadmap_data/topics/stage12_topic02.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
const long long MOD=1000000007;
long long modmul(long long a,long long b){
    return (a%MOD)*(b%MOD)%MOD;
}
long long modpow(long long a,long long e){
    long long r=1;
    while(e){
        if(e&1) r=r*a%MOD;
        a=a*a%MOD;
        e>>=1;
    }
    return r;
}
long long modinv(long long a){
    // MOD nguyên tố -> a^(MOD-2) mod MOD
    return modpow(a,MOD-2);
}
int main(){
    long long a,b;cin>>a>>b;
    cout<<"(a*b)%MOD="<<modmul(a,b)<<"\\n";
    cout<<"inverse(a)="<<modinv(a)<<"\\n";
}""",
            "sample_py": """MOD=10**9+7
def modmul(a,b):
    return (a%MOD)*(b%MOD)%MOD
def modpow(a,e):
    r=1
    while e:
        if e&1: r=r*a%MOD
        a=a*a%MOD
        e//=2
    return r
def modinv(a):
    # Fermat: a^(MOD-2) % MOD
    return modpow(a,MOD-2)
a,b=map(int,input().split())
print("(a*b)%MOD =",modmul(a,b))
print("inverse(a) =",modinv(a))"""
        },
        {
            "title": "12.3. Một số phương pháp kiểm tra số nguyên tố cơ bản",
            "summary": "Hiểu rõ ưu nhược điểm và cơ chế của các thuật toán kiểm tra số nguyên tố cơ bản.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/12/topic/3/",
            "html_file": "roadmap_data/topics/stage12_topic03.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
int main(){
    int n;cin>>n;
    vector<int> isPrime(n+1,1);
    isPrime[0]=isPrime[1]=0;
    for(int i=2;i*i<=n;i++){
        if(isPrime[i]){
            for(int j=i*i;j<=n;j+=i)
                isPrime[j]=0;
        }
    }
    for(int i=2;i<=n;i++)
        if(isPrime[i]) cout<<i<<" ";
}""",
            "sample_py": """n=int(input())
isPrime=[True]*(n+1)
isPrime[0]=isPrime[1]=False
p=2
while p*p<=n:
    if isPrime[p]:
        for j in range(p*p,n+1,p):
            isPrime[j]=False
    p+=1
print(*[i for i in range(2,n+1) if isPrime[i]])"""
        },
        {
            "title": "12.4. Tổ hợp & phân tích số",
            "summary": "Tính C(n,k), P(n,k) và phân tích số thành tổng hoặc tích các phần tử.",
            "lang_support": ["C++", "Python"],
            "more_url": "/stages/12/topic/4/",
            "html_file": "roadmap_data/topics/stage12_topic04.html",
            "sample_cpp": """#include <bits/stdc++.h>
using namespace std;
const long long MOD=1000000007;
long long modpow(long long a,long long e){
    long long r=1;
    while(e){
        if(e&1) r=r*a%MOD;
        a=a*a%MOD;
        e>>=1;
    }
    return r;
}
long long modinv(long long a){
    return modpow(a,MOD-2);
}
int main(){
    int n=10;
    vector<long long> fact(n+1,1),invfact(n+1,1);
    for(int i=1;i<=n;i++) fact[i]=fact[i-1]*i%MOD;
    invfact[n]=modinv(fact[n]);
    for(int i=n-1;i>=0;i--) invfact[i]=invfact[i+1]*(i+1)%MOD;
    auto C=[&](int n,int k){
        if(k<0||k>n) return 0LL;
        return fact[n]*invfact[k]%MOD*invfact[n-k]%MOD;
    };
    cout<<"C(10,3) mod = "<<C(10,3)<<"\\n";
}""",
            "sample_py": """MOD=10**9+7
def modpow(a,e):
    r=1
    while e:
        if e&1: r=r*a%MOD
        a=a*a%MOD
        e//=2
    return r
def modinv(a): return modpow(a,MOD-2)

n=10
fact=[1]*(n+1)
invfact=[1]*(n+1)
for i in range(1,n+1):
    fact[i]=fact[i-1]*i%MOD
invfact[n]=modinv(fact[n])
for i in range(n-1,-1,-1):
    invfact[i]=invfact[i+1]*(i+1)%MOD
def C(n,k):
    if k<0 or k>n: return 0
    return fact[n]*invfact[k]%MOD*invfact[n-k]%MOD
print("C(10,3) mod =",C(10,3))"""
        },
    ],
}
