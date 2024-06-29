# -*- coding: utf-8 -*-
"""
Created on Sat Jun 29 19:04:46 2024

@author: Nimra Noor
"""

import redis
import tiktoken
import json


def num_tokens_from_string(string: str) -> int:
        """
        Returns the number of tokens in a text string.
        Helper method for remove_urls_and_update_ai_dialog()
        """
        encoding_name = "cl100k_base"
        encoding = tiktoken.get_encoding(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens
    


def ensure_memory_limits(max_pairs, max_tokens, user_memory_key):
    
        
        
        # Connect to Redis
        r = redis.Redis()
        """
        Manages memory by keeping it below predefined limits (see control_variables.py)
        """
        
        user_memory_key =f"message_store:{user_memory_key}"


        # Retrieve all dialog pairs from Redis memory
        dialog_pairs = r.lrange(user_memory_key, 0, -1)  
        

        # Calculate the current number of pairs
        current_pairs = len(dialog_pairs) // 2

        # If the number of pairs exceeds the max limit, truncate it
        if current_pairs > max_pairs:
            truncate_count = (current_pairs - max_pairs) * 2  # Multiply by 2 because each pair consists of AI and human dialog
            dialog_pairs = dialog_pairs[:-truncate_count]

        # Count the total number of tokens across all remaining dialog pairs
        total_tokens = sum(num_tokens_from_string(json.loads(message)["data"]["content"]) for message in dialog_pairs)
        print("total tokens: ", total_tokens)

        # If the total number of tokens exceeds the max limit, further truncate dialog pairs
        while total_tokens > max_tokens:
            # Start removing pairs from the end until the total number of tokens is less than the max limit
            for _ in range(2):  # Remove both AI and human dialog from a pair
                if dialog_pairs:
                    pair = dialog_pairs.pop()
                    pair_tokens = num_tokens_from_string(json.loads(pair)["data"]["content"])
                    total_tokens -= pair_tokens
                else:
                    break

        # Reflect the truncation in Redis
        r.ltrim(user_memory_key, 0, len(dialog_pairs) - 1)
        print("Memory successfully limited")
        

    
