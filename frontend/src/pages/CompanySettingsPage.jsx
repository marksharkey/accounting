import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card } from '../components/ui/Card';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';

export default function CompanySettingsPage() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef(null);
  const [form, setForm] = useState({
    company_name: '',
    address_line1: '',
    address_line2: '',
    city: '',
    state: '',
    zip_code: '',
    phone: '',
    email: '',
    website_url: '',
  });
  const [message, setMessage] = useState({ type: '', text: '' });
  const [uploadingLogo, setUploadingLogo] = useState(false);

  // Fetch company info
  const { data: companyInfo, isLoading } = useQuery({
    queryKey: ['company-info'],
    queryFn: async () => {
      try {
        const response = await apiClient.get('/company-info/');
        setForm(response.data);
        return response.data;
      } catch (error) {
        if (error.response?.status === 404) {
          // First time setup - form starts empty
          return null;
        }
        throw error;
      }
    },
  });

  // Mutation for saving company info
  const saveInfoMutation = useMutation({
    mutationFn: (data) => {
      if (companyInfo?.id) {
        return apiClient.put('/company-info/', data);
      } else {
        return apiClient.put('/company-info/', data);
      }
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['company-info'], data);
      setMessage({ type: 'success', text: 'Company information saved successfully!' });
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
    },
    onError: (error) => {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to save company information',
      });
    },
  });

  // Mutation for logo upload
  const uploadLogoMutation = useMutation({
    mutationFn: async (file) => {
      const formData = new FormData();
      formData.append('file', file);
      return apiClient.post('/company-info/logo', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['company-info'], data);
      setMessage({ type: 'success', text: 'Logo uploaded successfully!' });
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
    },
    onError: (error) => {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to upload logo',
      });
    },
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.company_name.trim()) {
      setMessage({ type: 'error', text: 'Company name is required' });
      return;
    }
    saveInfoMutation.mutate(form);
  };

  const handleLogoChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const maxSize = 5 * 1024 * 1024; // 5MB
    if (file.size > maxSize) {
      setMessage({ type: 'error', text: 'Logo file must be under 5MB' });
      return;
    }

    setUploadingLogo(true);
    uploadLogoMutation.mutate(file);
    setUploadingLogo(false);
  };

  if (isLoading) {
    return <Layout title="Company Settings">Loading...</Layout>;
  }

  return (
    <Layout title="Company Settings">
      <div className="max-w-2xl">
        {/* Messages */}
        {message.text && (
          <div
            className={`mb-4 p-4 rounded ${
              message.type === 'success'
                ? 'bg-green-50 text-green-800 border border-green-200'
                : 'bg-red-50 text-red-800 border border-red-200'
            }`}
          >
            {message.text}
          </div>
        )}

        <Card>
          <div className="p-6">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Company Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Company Name *
                </label>
                <Input
                  type="text"
                  name="company_name"
                  value={form.company_name}
                  onChange={handleInputChange}
                  placeholder="e.g., PrecisionPros"
                  required
                />
              </div>

              {/* Logo Upload */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Logo
                </label>
                <div className="flex flex-col gap-4">
                  {companyInfo?.logo_url && (
                    <div className="flex justify-center">
                      <img
                        src={companyInfo.logo_url}
                        alt="Company Logo"
                        className="h-32 w-auto object-contain"
                      />
                    </div>
                  )}
                  <div>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      onChange={handleLogoChange}
                      className="block w-full text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                    />
                    <p className="text-xs text-gray-500 mt-1">PNG, JPG, GIF, SVG or WebP. Max 5MB.</p>
                  </div>
                </div>
              </div>

              {/* Address Section */}
              <div className="border-t pt-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Address</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Address Line 1
                    </label>
                    <Input
                      type="text"
                      name="address_line1"
                      value={form.address_line1 || ''}
                      onChange={handleInputChange}
                      placeholder="e.g. 123 Main St"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Address Line 2
                    </label>
                    <Input
                      type="text"
                      name="address_line2"
                      value={form.address_line2 || ''}
                      onChange={handleInputChange}
                      placeholder="e.g. Suite 100 (optional)"
                    />
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        City
                      </label>
                      <Input
                        type="text"
                        name="city"
                        value={form.city || ''}
                        onChange={handleInputChange}
                        placeholder="e.g. San Francisco"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        State
                      </label>
                      <Input
                        type="text"
                        name="state"
                        value={form.state || ''}
                        onChange={handleInputChange}
                        placeholder="e.g. CA"
                        maxLength={2}
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Zip Code
                      </label>
                      <Input
                        type="text"
                        name="zip_code"
                        value={form.zip_code || ''}
                        onChange={handleInputChange}
                        placeholder="e.g. 90210"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Contact Section */}
              <div className="border-t pt-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Contact Information</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Phone
                    </label>
                    <Input
                      type="tel"
                      name="phone"
                      value={form.phone || ''}
                      onChange={handleInputChange}
                      placeholder="e.g. (555) 123-4567"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Email
                    </label>
                    <Input
                      type="email"
                      name="email"
                      value={form.email || ''}
                      onChange={handleInputChange}
                      placeholder="e.g. hello@company.com"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Website
                    </label>
                    <Input
                      type="url"
                      name="website_url"
                      value={form.website_url || ''}
                      onChange={handleInputChange}
                      placeholder="e.g. https://yourcompany.com"
                    />
                  </div>
                </div>
              </div>

              {/* Save Button */}
              <div className="border-t pt-6 flex gap-3">
                <Button
                  type="submit"
                  disabled={saveInfoMutation.isPending || uploadingLogo}
                >
                  {saveInfoMutation.isPending ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            </form>
          </div>
        </Card>
      </div>
    </Layout>
  );
}
