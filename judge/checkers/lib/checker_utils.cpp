#include <bits/stdc++.h>
using namespace std;

int read_int(istream& in) {
    int x;
    if (!(in >> x)) throw runtime_error("read_int failed");
    return x;
}

vector<int> read_vector(istream& in, int n) {
    vector<int> a(n);
    for (int i = 0; i < n; ++i) in >> a[i];
    return a;
}

vector<vector<int>> read_matrix(istream& in, int r, int c) {
    vector<vector<int>> m(r, vector<int>(c));
    for (int i = 0; i < r; ++i)
        for (int j = 0; j < c; ++j)
            in >> m[i][j];
    return m;
}

bool verify_permutation(const vector<int>& a, int n) {
    if ((int)a.size() != n) return false;
    vector<int> seen(n + 1, 0);
    for (int x : a) {
        if (x < 1 || x > n || seen[x]) return false;
        seen[x] = 1;
    }
    return true;
}

bool verify_graph_path(const vector<int>& path, const vector<pair<int,int>>& edges, bool directed=false) {
    set<pair<int,int>> st(edges.begin(), edges.end());
    if (!directed) {
        for (auto [u,v] : edges) st.insert({v,u});
    }
    for (int i = 0; i + 1 < (int)path.size(); ++i) {
        if (!st.count({path[i], path[i+1]})) return false;
    }
    return !path.empty();
}

bool verify_matching(const vector<pair<int,int>>& matching, const vector<pair<int,int>>& edges) {
    set<pair<int,int>> est(edges.begin(), edges.end());
    set<int> left, right;
    for (auto [u,v] : matching) {
        if (!est.count({u,v})) return false;
        if (!left.insert(u).second) return false;
        if (!right.insert(v).second) return false;
    }
    return true;
}
