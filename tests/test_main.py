from unittest.mock import MagicMock, patch
import pytest
from genpass.main import generate_passphrase, generate_password, load_portuguese_words

@pytest.fixture
def mock_dependencies():
    """Extreme unit isolation mock simulation environment fixture."""
    with patch("secrets.choice") as mock_choice, \
         patch("secrets.SystemRandom") as mock_sys_random, \
         patch("urllib.request.urlopen") as mock_urlopen:
        
        # Setup shuffle mock tracking mechanics
        mock_shuffle = MagicMock()
        mock_sys_random.return_value.shuffle = mock_shuffle
        
        yield {
            "choice": mock_choice,
            "shuffle": mock_shuffle,
            "urlopen": mock_urlopen
        }

def test_load_portuguese_words_extreme_mock_network_success(mock_dependencies):
    """Verify clean downstream sanitization paths when remote streams load normally."""
    mock_response = MagicMock()
    mock_response.read.return_value = b"Abacaxi\nJanela\nCripto123\nSol\n"
    mock_dependencies["urlopen"].return_value.__enter__.return_value = mock_response

    words = load_portuguese_words()
    # Should lowercase valid strings and drop those out of character limits
    assert "abacaxi" in words
    assert "janela" in words
    assert "sol" not in words  # Less than 4 characters

def test_load_portuguese_words_extreme_mock_network_failure(mock_dependencies):
    """Verify bulletproof fallback array triggers instantly on systemic socket timeouts."""
    mock_dependencies["urlopen"].side_effect = Exception("System Socket Timeout")
    
    words = load_portuguese_words()
    assert "computador" in words
    assert len(words) == 10

@patch("genpass.main.load_portuguese_words")
def test_generate_passphrase_deterministic_selection(mock_load, mock_dependencies):
    """Enforce exact cryptographic alignment patterns under static word selections."""
    mock_load.return_value = ["mockedword"]
    mock_dependencies["choice"].return_value = "mockedword"

    passphrase = generate_passphrase(word_count=3, separator=":")
    assert passphrase == "mockedword:mockedword:mockedword"
    assert mock_dependencies["choice"].call_count == 3

def test_generate_password_first_char_constraints(mock_dependencies):
    """Verify absolute structural alignment properties on specified initialization hooks."""
    # Force 'A' for the first choice, then 'b' for remaining loops
    mock_dependencies["choice"].side_effect = ["A", "b", "b", "b", "b"]

    password = generate_password(length=5, special_count=0, first_char_type="uppercase")
    assert password.startswith("A")
    assert len(password) == 5

def test_generate_password_blacklist_enforcement():
    """Ensure strict ValueError raising path triggers when parameters breach blacklists."""
    with pytest.raises(ValueError, match="Error: The first character .* is blacklisted"):
        generate_password(length=8, special_count=0, blacklist="X", first_char_type="X")
