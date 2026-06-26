#include <iostream>

int* createArray(int size) {
    int* arr = new int[size];
    return arr;
}

void checkPointer(int* ptr) {
    if (ptr == NULL) {
        std::cout << "Null pointer!" << std::endl;
    }
}

void processValue(double val) {
    int result = (int)val;
    std::cout << result << std::endl;
}

int main() {
    int* myArr = createArray(10);
    checkPointer(myArr);
    delete[] myArr;
    return 0;
}