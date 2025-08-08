#include <bits/stdc++.h>
using namespace std;

class SegmentTree {
private:
    vector<int> tree;
    int size;

    void build(const vector<int>& arr, int node, int start, int end) {
        if (start == end) {
            tree[node] = arr[start];
            return;
        }
        int mid = (start + end) / 2;
        build(arr, 2 * node, start, mid);
        build(arr, 2 * node + 1, mid + 1, end);
        tree[node] = tree[2 * node] + tree[2 * node + 1];
    }

    int query(int node, int start, int end, int left, int right) {
        if (right < start || end < left)
            return 0;  // no overlap
        if (left <= start && end <= right)
            return tree[node];  // total overlap

        int mid = (start + end) / 2;
        int leftSum = query(2 * node, start, mid, left, right);
        int rightSum = query(2 * node + 1, mid + 1, end, left, right);
        return leftSum + rightSum;
    }

    void update(int node, int start, int end, int index, int value) {
        if (start == end) {
            tree[node] = value;
            return;
        }
        int mid = (start + end) / 2;
        if (index <= mid)
            update(2 * node, start, mid, index, value);
        else
            update(2 * node + 1, mid + 1, end, index, value);
        tree[node] = tree[2 * node] + tree[2 * node + 1];
    }

public:
    SegmentTree(const vector<int>& arr) {
        size = (int)arr.size();
        tree.resize(4 * size);
        build(arr, 1, 0, size - 1);
    }

    int query(int left, int right) {
        return query(1, 0, size - 1, left, right);
    }

    void update(int index, int value) {
        update(1, 0, size - 1, index, value);
    }
};

int main() {
    vector<int> arr = {1, 3, 5, 7, 9, 11};
    SegmentTree segTree(arr);

    cout << "Sum of range [1, 3]: " << segTree.query(1, 3) << "\n";  // 15

    segTree.update(1, 10);  // arr[1] = 10

    cout << "After update, sum of range [1, 3]: " << segTree.query(1, 3) << "\n";  // 22

    return 0;
}
