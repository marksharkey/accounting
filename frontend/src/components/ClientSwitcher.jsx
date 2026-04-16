import { useState, useRef, memo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, X } from 'lucide-react';

function ClientSwitcherComponent({ currentClientId, currentClientName, allClients }) {
  const [searchInput, setSearchInput] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  const handleSearch = () => {
    if (!searchInput.trim()) {
      setSearchResults([]);
      return;
    }

    const query = searchInput.toLowerCase();
    const results = (allClients || []).filter(c => {
      const companyName = c.company_name?.toLowerCase() || '';
      const contactName = c.contact_name?.toLowerCase() || '';
      const email = c.email?.toLowerCase() || '';
      const phone = c.phone?.toLowerCase() || '';
      const address1 = c.address_line1?.toLowerCase() || '';
      const address2 = c.address_line2?.toLowerCase() || '';
      const city = c.city?.toLowerCase() || '';
      const state = c.state?.toLowerCase() || '';
      const zip = c.zip_code?.toLowerCase() || '';

      return (
        companyName.includes(query) ||
        contactName.includes(query) ||
        email.includes(query) ||
        phone.includes(query) ||
        address1.includes(query) ||
        address2.includes(query) ||
        city.includes(query) ||
        state.includes(query) ||
        zip.includes(query)
      );
    });

    setSearchResults(results);
    setIsSearching(true);
  };

  const handleSelectClient = (clientId) => {
    navigate(`/clients/${clientId}`);
    setSearchInput('');
    setSearchResults([]);
    setIsSearching(false);
  };

  const handleClearSearch = () => {
    setSearchInput('');
    setSearchResults([]);
    setIsSearching(false);
    inputRef.current?.focus();
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm font-medium text-gray-700">
        Client: <span className="font-semibold text-gray-900">{currentClientName}</span>
      </span>
      <div className="relative">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            placeholder="Search by name, email, address..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyPress={handleKeyPress}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-64"
            autoComplete="off"
          />
          <button
            onClick={handleSearch}
            className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm flex items-center gap-1"
          >
            <Search className="w-4 h-4" />
            Search
          </button>
          {isSearching && (
            <button
              onClick={handleClearSearch}
              className="px-3 py-2 bg-gray-300 hover:bg-gray-400 text-gray-700 rounded-md text-sm flex items-center gap-1"
            >
              <X className="w-4 h-4" />
              Clear
            </button>
          )}
        </div>

        {isSearching && (
          <div className="absolute top-full left-0 right-0 mt-2 bg-white border border-gray-300 rounded-md shadow-lg z-50 max-h-64 overflow-y-auto">
            {searchResults.length > 0 ? (
              searchResults.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => handleSelectClient(c.id)}
                  className={`w-full text-left px-4 py-3 border-b last:border-b-0 hover:bg-blue-50 transition-colors ${
                    c.id === parseInt(currentClientId) ? 'bg-blue-100 font-medium' : ''
                  }`}
                >
                  <div className="font-medium">{c.company_name}</div>
                  <div className="text-xs text-gray-600">
                    {c.contact_name && <div>{c.contact_name}</div>}
                    {c.email && <div>{c.email}</div>}
                    {c.city && <div>{c.city}, {c.state}</div>}
                  </div>
                </button>
              ))
            ) : (
              <div className="px-4 py-3 text-sm text-gray-500">No clients found</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default memo(ClientSwitcherComponent);
