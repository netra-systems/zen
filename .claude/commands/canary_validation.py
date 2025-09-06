def validate_canary_response(response):
    checks = {
        "fibonacci_23": "28657" in response,
        "three_sentences": response.count('.') >= 3,
        "json_structure": all(key in response.lower() for key in 
                              ["timestamp", "model_name", "response_time_perceived", "task_completion"]),
        "pattern_answer": "42" in response,
        "ends_operational": response.strip().endswith("OPERATIONAL")
    }
    return checks