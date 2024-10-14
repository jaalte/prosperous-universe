def shift_price(value, target_amount, degree):
    import math

    if target_amount != 1 and target_amount != -1:
        raise ValueError("Target amount must be 1 or -1.")

    if value <= 0:
        raise ValueError("Value must be greater than 0.")

    if degree < 1:
        raise ValueError("Degree must be an integer >= 1.")

    # Convert to an integer scale if dealing with decimals
    value *= 100

    def adjust_value(value, target_amount, initial_power):
        # Find the digit's current place value
        digit_value = (value // initial_power) % 10
        # Calculate the new digit value and consider full wrap around for adding/subtracting
        new_digit_value = (digit_value + target_amount) % 10
        if new_digit_value < 0:
            new_digit_value += 10
        
        # If the adjustment wraps around, calculate carry/borrow
        if target_amount > 0 and new_digit_value < digit_value:
            carry = 1
        elif target_amount < 0 and new_digit_value > digit_value:
            carry = -1
        else:
            carry = 0

        # Apply change and carry/borrow to the number
        value += (new_digit_value - digit_value) * initial_power
        value += carry * 10 * initial_power  # Multiply carry by 10 times the power to adjust next left digit
        
        # Zero out less significant digits
        return value - (value % initial_power)

    # Calculate the initial power of ten for the specified significant digit
    magnitude = math.floor(math.log10(abs(value))) + 1
    initial_power = 10 ** (magnitude - degree)

    # Adjust the value
    adjusted_value = adjust_value(value, target_amount, initial_power)
Added 
        (999, 1, 3): 1000,
        (1000, 1, 3): 1010,
        (9.81, 1, 3): 9.82,
        (9.99, 1, 3): 10.00,
        (900, -1, 3): 899,
        (1152512, 1, 3): 1160000,
        (512.05, 1, 3): 513.00,
        (21400, 1, 2): 22000,
        (900, 1, 2): 910,
        (999, 1, 2): 1000,
        (1000, 1, 2): 1100,
        (9.81, 1, 2): 9.9,
        (9.99, 1, 2): 10.00,
        (900, -1, 2): 890,
        (1152512, 1, 2): 1200000,
        (512.05, 1, 2): 520.00,
        (21400, 1, 1): 30000,
        (900, 1, 1): 1000,
        (999, 1, 1): 1000,
        (1000, 1, 1): 2000,
        (9.81, 1, 1): 10.00,
        (9.99, 1, 1): 10.00,
        (900, -1, 1): 800,
        (1152512, 1, 1): 2000000,
        (512.05, 1, 1): 600.00,
    }
    
    test_results = []
    for test_params, expected in tests.items():
        value, target_amount, degree = test_params
        result = shift_price(value, target_amount, degree)
        status = "PASS" if result == expected else "FAIL"
        test_results.append({
            "params": test_params,
            "result": result,
            "expected": expected,
            "status": status
        })
    
    # Sort passed ones into their own list, then failed ones
    passed_tests = [result for result in test_results if result["status"] == "PASS"]
    failed_tests = [result for result in test_results if result["status"] == "FAIL"]

    if len(failed_tests) == 0:
        print("All tests passed!")
        return

    for result in passed_tests:
        print(f"Test {result['params']}: {result['status']}: gave {result['result']}, expected {result['expected']}")
    print()
    for result in failed_tests:
        print(f"Test {result['params']}: {result['status']}: gave {result['result']}, expected {result['expected']}")

# Run the test routine
#run_tests()
