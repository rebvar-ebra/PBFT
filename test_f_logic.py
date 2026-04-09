def calculate_f(n):
    return (n - 1) // 3

test_cases = [
    (1, 0),
    (4, 1),
    (7, 2),
    (10, 3)
]

for n, expected_f in test_cases:
    actual_f = calculate_f(n)
    assert actual_f == expected_f, f"For n={n}, expected f={expected_f}, but got {actual_f}"
    print(f"n={n}: f={actual_f} [OK]")

print("All fault tolerance logic tests passed!")
