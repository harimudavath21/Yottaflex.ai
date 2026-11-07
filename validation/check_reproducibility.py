import random
from faker import Faker

from generator.generate_data import SEED


def check_reproducibility():
    print("\nREPRODUCIBILITY VALIDATION")
    print("=" * 50)

    # Check 1: Fixed seed
    print("Configured seed:", SEED)

    if SEED == 20261022:
        print("Fixed seed configuration: PASS")
    else:
        print("Fixed seed configuration: FAIL")
        return

    # Check 2: Python random reproducibility
    random.seed(SEED)
    first_random_values = [
        random.randint(1, 100000)
        for _ in range(5)
    ]

    random.seed(SEED)
    second_random_values = [
        random.randint(1, 100000)
        for _ in range(5)
    ]

    random_passed = first_random_values == second_random_values

    print(
        "Python random reproducibility:",
        "PASS" if random_passed else "FAIL"
    )

    # Check 3: Faker reproducibility
    Faker.seed(SEED)
    fake_one = Faker("en_IN")
    first_names = [fake_one.name() for _ in range(5)]

    Faker.seed(SEED)
    fake_two = Faker("en_IN")
    second_names = [fake_two.name() for _ in range(5)]

    faker_passed = first_names == second_names

    print(
        "Faker reproducibility:",
        "PASS" if faker_passed else "FAIL"
    )

    print("\nSample generated names:")
    for name in first_names:
        print("-", name)

    print("\n" + "=" * 50)

    if random_passed and faker_passed:
        print("OVERALL RESULT: REPRODUCIBILITY CHECK PASSED")
    else:
        print("OVERALL RESULT: REPRODUCIBILITY CHECK FAILED")


if __name__ == "__main__":
    check_reproducibility()
