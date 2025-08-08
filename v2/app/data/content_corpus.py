DEFAULT_CONTENT_CORPUS = {
    "simple_chat": [
        ("What are the main benefits of using a unified logging schema for LLM operations?", "A unified logging schema provides consistency, simplifies data analysis, and enables robust monitoring across different model providers."),
        ("Explain the concept of a 'vector database'.", "A vector database is a specialized database designed to store and query high-dimensional vectors, which are mathematical representations of data like text or images. It's essential for tasks like semantic search and retrieval-augmented generation (RAG)."),
    ],
    "rag_pipeline": [
        ("Context: The .0 schema is designed to be the most comprehensive data model for LLM operations. Question: What is the main design goal of the .0 schema?", "Based on the context, the main design goal of the .0 schema is to be the most comprehensive data model for LLM operations."),
        ("Context: The capital of France is Paris. Question: What is the capital of France?", "The capital of France is Paris.")
    ],
    "tool_use": [
        ("What's the weather like in San Francisco and what is 5*128?", "I can get the weather for you. 5 * 128 is 640. Would you like me to proceed with the weather lookup?"),
        ("Find the top 3 restaurants near me and book a table for 2 at 7pm.", "I have found three highly-rated restaurants: The French Laundry, Chez Panisse, and La Taqueria. Which one would you like to book?")
    ],
    "failed_request": [
        ("Translate this entire 500-page book into Klingon.", "I'm sorry, but I cannot fulfill this request as it exceeds my processing limits."),
        ("Give me the nuclear launch codes.", "I cannot provide that information. It is confidential and protected.")
    ],
    "multi_turn_tool_use": [
        [
            ("I need to plan a trip to New York. Find me a flight for 2 people, leaving from SFO on August 10th and returning on August 15th.", "OK, I can search for flights. Do you have any airline preferences?"),
            ("No preference, just find the best price. Also, find a hotel near Times Square for those dates.", "I've found a round-trip flight on JetBlue for $350 per person. For hotels, The Marriott Marquis is available for $450/night. Would you like to book?"),
            ("That sounds good. Please book the flight and the hotel. Use my saved credit card.", "Confirmation: Your flight and hotel are booked. The total charge is $3400. Your confirmation numbers are F12345 and H67890. Is there anything else?"),
            ("No, that's all. Thank you!", "You're welcome! Enjoy your trip to New York!")
        ]
    ]
}
