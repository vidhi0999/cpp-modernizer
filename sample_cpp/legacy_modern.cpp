#include <iostream>
#include <memory>

std::unique_ptr<int[]> createArray(int size) {
    return std::make_unique<int[]>(size);
}

void checkPointer(const std::unique_ptr<int[]>& ptr) {
    if (!ptr) {
        std::cout << "Null pointer!" << std::endl;
    }
}

void processValue(double val) {
    int result = static_cast<int>(val);
    std::cout << result << std::endl;
}

int main() {
    std::unique_ptr<int[]> myArr = createArray(10);
    checkPointer(myArr);
    double d = 10.5;
    processValue(d);
    return 0;
}