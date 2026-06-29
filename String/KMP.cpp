// KMP (Knuth-Morris-Pratt) Pattern Matching Algorithm
//
// Time Complexity:
// 1. Building LPS Array  : O(m)
// 2. Pattern Searching   : O(n)
// Total                  : O(n + m)
//
// Space Complexity:
// LPS Array              : O(m)
//
// where:
// n = length of text
// m = length of pattern
//
// ---------------------------------------------------
// Interview Memory Trick
// ---------------------------------------------------
//
// LPS[i] = length of the longest proper prefix
//          which is also a suffix
//          for pattern[0...i]
//
// During Search:
//
// i = text pointer
// j = pattern pointer
//
// Match      -> i++, j++
//
// Full Match -> j = lps[j - 1]
//
// Mismatch   -> j = lps[j - 1]
//               OR
//               i++ if j == 0
//
// If you remember the above 4 rules,
// you can usually reconstruct the
// entire KMP algorithm in an interview.
//
// ---------------------------------------------------

#include <iostream>
#include <vector>
using namespace std;

// Build LPS (Longest Prefix Suffix) Array
vector<int> buildLPS(string pattern) {
    int m = pattern.size();
    vector<int> lps(m, 0);

    int len = 0; // length of current longest prefix-suffix
    int i = 1;

    while (i < m) {

        if (pattern[i] == pattern[len]) {
            len++;
            lps[i] = len;
            i++;
        }
        else {

            if (len != 0) {
                len = lps[len - 1];
            }
            else {
                lps[i] = 0;
                i++;
            }
        }
    }

    return lps;
}

// KMP Search
vector<int> KMP(string text, string pattern) {

    vector<int> result;

    int n = text.size();
    int m = pattern.size();

    vector<int> lps = buildLPS(pattern);

    int i = 0; // text pointer
    int j = 0; // pattern pointer

    while (i < n) {

        // Character match
        if (text[i] == pattern[j]) {
            i++;
            j++;
        }

        // Complete pattern matched
        if (j == m) {
            result.push_back(i - j); // 0-based index
            j = lps[j - 1];
        }

        // Character mismatch
        else if (i < n && text[i] != pattern[j]) {

            if (j != 0) {
                j = lps[j - 1];
            }
            else {
                i++;
            }
        }
    }

    return result;
}

int main() {

    string text = "ABABAB";
    string pattern = "ABAB";

    vector<int> matches = KMP(text, pattern);

    for (int idx : matches) {
        cout << "Pattern found at index: " << idx << endl;
    }

    return 0;
}