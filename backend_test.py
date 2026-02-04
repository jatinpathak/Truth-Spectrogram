import requests
import sys
import base64
import json
import io
from datetime import datetime

class VoiceDetectionAPITester:
    def __init__(self, base_url="https://speak-verify-1.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.valid_api_key = "sk_test_voice_detection_2026"
        self.tests_run = 0
        self.tests_passed = 0
        self.languages = ["Tamil", "English", "Hindi", "Malayalam", "Telugu"]
        
    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {response_data}")
                except:
                    print(f"   Response: {response.text[:200]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text}")
            
            return success, response
            
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, None
    
    def create_dummy_mp3_base64(self):
        """Create a dummy MP3-like base64 string for testing"""
        # This is a minimal MP3 header + some audio data
        mp3_header = b'\xff\xfb\x90\x00' + b'\x00' * 100  # Simplified MP3 header
        return base64.b64encode(mp3_header).decode('utf-8')
    
    def test_api_root(self):
        """Test API root endpoint"""
        return self.run_test("API Root", "GET", "", 200)
    
    def test_health_check(self):
        """Test health check endpoint"""
        return self.run_test("Health Check", "GET", "health", 200)
    
    def test_voice_detection_no_api_key(self):
        """Test voice detection without API key"""
        data = {
            "language": "English",
            "audioFormat": "mp3",
            "audioBase64": self.create_dummy_mp3_base64()
        }
        return self.run_test(
            "Voice Detection - No API Key", 
            "POST", 
            "voice-detection", 
            401, 
            data=data
        )
    
    def test_voice_detection_invalid_api_key(self):
        """Test voice detection with invalid API key"""
        data = {
            "language": "English", 
            "audioFormat": "mp3",
            "audioBase64": self.create_dummy_mp3_base64()
        }
        headers = {"x-api-key": "invalid_key_123", "Content-Type": "application/json"}
        return self.run_test(
            "Voice Detection - Invalid API Key",
            "POST", 
            "voice-detection", 
            401, 
            data=data, 
            headers=headers
        )
    
    def test_voice_detection_valid_request(self):
        """Test voice detection with valid API key and data"""
        data = {
            "language": "English",
            "audioFormat": "mp3", 
            "audioBase64": self.create_dummy_mp3_base64()
        }
        headers = {"x-api-key": self.valid_api_key, "Content-Type": "application/json"}
        success, response = self.run_test(
            "Voice Detection - Valid Request",
            "POST",
            "voice-detection", 
            200,
            data=data,
            headers=headers
        )
        
        if success and response:
            try:
                result = response.json()
                # Validate response structure
                required_fields = ["status", "language", "classification", "confidenceScore", "explanation"]
                missing_fields = [field for field in required_fields if field not in result]
                if missing_fields:
                    print(f"❌ Missing response fields: {missing_fields}")
                    return False, response
                
                # Validate classification values
                if result["classification"] not in ["AI_GENERATED", "HUMAN"]:
                    print(f"❌ Invalid classification: {result['classification']}")
                    return False, response
                
                # Validate confidence score range
                if not (0.0 <= result["confidenceScore"] <= 1.0):
                    print(f"❌ Invalid confidence score: {result['confidenceScore']}")
                    return False, response
                    
                print("✅ Response structure validation passed")
                return True, response
                
            except Exception as e:
                print(f"❌ Response validation failed: {str(e)}")
                return False, response
                
        return success, response
    
    def test_all_languages(self):
        """Test voice detection for all supported languages"""
        results = []
        headers = {"x-api-key": self.valid_api_key, "Content-Type": "application/json"}
        
        for language in self.languages:
            data = {
                "language": language,
                "audioFormat": "mp3",
                "audioBase64": self.create_dummy_mp3_base64()
            }
            success, response = self.run_test(
                f"Language Support - {language}",
                "POST",
                "voice-detection",
                200,
                data=data,
                headers=headers
            )
            results.append((language, success))
            
        return results
    
    def test_invalid_language(self):
        """Test voice detection with invalid language"""
        data = {
            "language": "French",  # Not supported
            "audioFormat": "mp3",
            "audioBase64": self.create_dummy_mp3_base64()
        }
        headers = {"x-api-key": self.valid_api_key, "Content-Type": "application/json"}
        return self.run_test(
            "Invalid Language",
            "POST",
            "voice-detection",
            400,
            data=data,
            headers=headers
        )
    
    def test_invalid_audio_format(self):
        """Test voice detection with invalid audio format"""
        data = {
            "language": "English",
            "audioFormat": "wav",  # Not supported
            "audioBase64": self.create_dummy_mp3_base64()
        }
        headers = {"x-api-key": self.valid_api_key, "Content-Type": "application/json"}
        return self.run_test(
            "Invalid Audio Format",
            "POST", 
            "voice-detection",
            400,
            data=data,
            headers=headers
        )
    
    def test_invalid_base64(self):
        """Test voice detection with invalid base64"""
        data = {
            "language": "English",
            "audioFormat": "mp3",
            "audioBase64": "invalid_base64_data!!!"
        }
        headers = {"x-api-key": self.valid_api_key, "Content-Type": "application/json"}
        return self.run_test(
            "Invalid Base64",
            "POST",
            "voice-detection",
            400,
            data=data,
            headers=headers
        )

def main():
    """Run all API tests"""
    print("🚀 Starting AI Voice Detection API Tests")
    print("=" * 50)
    
    tester = VoiceDetectionAPITester()
    
    # Test basic endpoints
    tester.test_api_root()
    tester.test_health_check()
    
    # Test authentication
    tester.test_voice_detection_no_api_key()
    tester.test_voice_detection_invalid_api_key()
    
    # Test valid request
    tester.test_voice_detection_valid_request()
    
    # Test all supported languages
    language_results = tester.test_all_languages()
    
    # Test error cases
    tester.test_invalid_language()
    tester.test_invalid_audio_format()
    tester.test_invalid_base64()
    
    # Print final results
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Total Tests: {tester.tests_run}")
    print(f"Passed: {tester.tests_passed}")
    print(f"Failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    # Language support summary
    print("\n🌍 Language Support:")
    for language, success in language_results:
        status = "✅" if success else "❌"
        print(f"  {status} {language}")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())