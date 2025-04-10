# utils/api_utils.py
import time

def retry_api_call(retry_function, *args, **kwargs):
    """
    Retries API calls when the Gemini model server is unavailable or encounters errors.

    Args:
        retry_function: The function to retry (either generate_prompt or the model API call)
        *args, **kwargs: Arguments to pass to the function

    Returns:
        The result of the successful function call, or None after maximum retries
    """
    max_consecutive_failures = 1000  # Effectively keep trying indefinitely
    retry_delay = 10  # seconds
    attempt = 0

    while attempt < max_consecutive_failures:
        attempt += 1
        try:
            print(f"⏳ API call attempt {attempt}...")
            result = retry_function(*args, **kwargs)

            # For generate function, check if we got story and images
            if retry_function.__name__ == 'generate_content_stream' or retry_function.__name__ == 'generate_content':
                # Success criteria - we need to check the response for both text and images
                if result:
                    # Check if the result contains "**Image Description:**" which indicates
                    # the model generated text descriptions instead of actual images

                    # For non-streaming responses in 0.8.4 version
                    if isinstance(result, dict) and 'candidates' in result and result['candidates']:
                        for candidate in result['candidates']:
                            if isinstance(candidate, dict) and 'content' in candidate and candidate['content']:
                                for part in candidate['content'].get('parts', []):
                                    if isinstance(part, dict) and 'text' in part and "**Image Description:**" in part['text']:
                                        print(f"⚠️ Model generated text descriptions instead of images on attempt {attempt}, retrying in {retry_delay} seconds...")
                                        time.sleep(retry_delay)
                                        continue

                    # For streaming responses, we can't easily check the content before consuming the stream
                    # So we'll rely on the subsequent processing to detect this issue

                    print(f"✅ API call successful on attempt {attempt}")
                    return result
                else:
                    print(f"⚠️ API returned empty result on attempt {attempt}, retrying in {retry_delay} seconds...")
            else:
                # For other functions like generate_prompt, just check if result is not None
                if result is not None:
                    print(f"✅ API call successful on attempt {attempt}")
                    return result
                else:
                    print(f"⚠️ API returned None on attempt {attempt}, retrying in {retry_delay} seconds...")
        
        except Exception as e:
            print(f"⚠️ API error on attempt {attempt}: {e}")
            
            # Handle various API errors with appropriate retry logic
            if "500 Internal Server Error" in str(e):
                print(f"⚠️ Server error (500), retrying in {retry_delay} seconds...")
            elif "503 Service Unavailable" in str(e):
                print(f"⚠️ Service unavailable (503), retrying in {retry_delay} seconds...")
            elif "429 Too Many Requests" in str(e):
                print(f"⚠️ Rate limited (429), waiting longer before retry...")
                # Wait longer for rate limit errors
                time.sleep(retry_delay * 2)
                continue
            elif "400 Bad Request" in str(e):
                print(f"⚠️ Bad request (400), may be an issue with prompt. Retrying anyway...")
            elif "ResourceExhausted" in str(e):
                print(f"⚠️ Resource exhausted, retrying in {retry_delay} seconds...")
            elif "grpc" in str(e).lower() or "deadline exceeded" in str(e).lower():
                print(f"⚠️ GRPC communication error, retrying in {retry_delay} seconds...")
            elif "model not found" in str(e).lower():
                print(f"⚠️ Model not found, check model name. Retrying in {retry_delay} seconds...")
            elif "content_blocked" in str(e).lower() or "blocked_reason" in str(e).lower():
                print(f"⚠️ Content blocked by safety settings. Adjusting request and retrying...")
            else:
                print(f"⚠️ Unknown error, retrying in {retry_delay} seconds...")
                
        # Wait before retrying
        time.sleep(retry_delay)
    
    print(f"❌ Failed after {max_consecutive_failures} attempts")
    return None
