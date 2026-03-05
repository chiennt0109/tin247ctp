# arena/forms.py
from django import forms
from .models import ArenaRun

DEFAULT_CPP = r"""#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int H, W, T;
    if (!(cin >> H >> W >> T)) return 0;
    vector<string> grid(H);
    for (int i = 0; i < H; ++i) cin >> grid[i];

    // Bot rất đơn giản: luôn đi RIGHT
    for (int i = 0; i < T; ++i) {
        cout << "RIGHT\n";
    }
    return 0;
}
""".strip()

DEFAULT_PY = r"""import sys

def main():
    data = sys.stdin.read().strip().splitlines()
    if not data:
        return
    H, W, T = map(int, data[0].split())
    grid = data[1:1+H]

    # Bot rất đơn giản: luôn đi RIGHT
    for _ in range(T):
        print("RIGHT")

if __name__ == "__main__":
    main()
""".strip()


class SnakeRunForm(forms.ModelForm):
    class Meta:
        model = ArenaRun
        fields = ("language", "source_code")

    language = forms.ChoiceField(
        choices=ArenaRun.LANG_CHOICES,
        initial=ArenaRun.LANG_CPP,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"})
    )

    source_code = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 20, "class": "form-control font-monospace"}),
        label="Mã nguồn bot"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get("source_code") and not self.data:
            # default C++ template
            self.initial["source_code"] = DEFAULT_CPP

    def clean_source_code(self):
        code = self.cleaned_data["source_code"]
        if not code.strip():
            raise forms.ValidationError("Vui lòng nhập mã nguồn.")
        return code
