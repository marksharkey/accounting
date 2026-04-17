import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card } from '../components/ui/Card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/Table';
import Button from '../components/ui/Button';
import AddServiceModal from '../components/AddServiceModal';

export default function ServiceCatalogPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedService, setSelectedService] = useState(null);
  const [sortColumn, setSortColumn] = useState('name');
  const [sortDirection, setSortDirection] = useState('asc');

  const { data: servicesData, isLoading } = useQuery({
    queryKey: ['services'],
    queryFn: async () => {
      const response = await apiClient.get('/services/');
      return response.data;
    },
  });

  const services = servicesData?.items || [];

  if (isLoading) {
    return <Layout title="Service Catalog">Loading...</Layout>;
  }

  const handleAddClick = () => {
    setSelectedService(null);
    setIsModalOpen(true);
  };

  const handleEditClick = (service) => {
    setSelectedService(service);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedService(null);
  };

  const handleSort = (column) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const getSortedServices = () => {
    const sorted = [...services].sort((a, b) => {
      let aVal = a[sortColumn];
      let bVal = b[sortColumn];

      // Handle numeric columns
      if (sortColumn === 'default_amount') {
        aVal = parseFloat(aVal) || 0;
        bVal = parseFloat(bVal) || 0;
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }

      // Handle string comparisons
      aVal = String(aVal || '').toLowerCase();
      bVal = String(bVal || '').toLowerCase();
      if (sortDirection === 'asc') {
        return aVal.localeCompare(bVal);
      } else {
        return bVal.localeCompare(aVal);
      }
    });
    return sorted;
  };

  const SortableHeader = ({ column, label }) => {
    const isActive = sortColumn === column;
    const indicator = isActive ? (sortDirection === 'asc' ? ' ↑' : ' ↓') : '';
    return (
      <TableHead
        onClick={() => handleSort(column)}
        className="cursor-pointer select-none hover:bg-gray-100"
        title={`Sort by ${label}`}
      >
        {label}{indicator}
      </TableHead>
    );
  };

  const sortedServices = getSortedServices();

  return (
    <Layout title="Service Catalog">
      <div className="mb-6">
        <Button onClick={handleAddClick}>+ Add Service</Button>
      </div>

      <AddServiceModal isOpen={isModalOpen} onClose={handleCloseModal} service={selectedService} />

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <SortableHeader column="name" label="Name" />
              <SortableHeader column="category" label="Category" />
              <SortableHeader column="default_amount" label="Default Amount" />
              <SortableHeader column="default_cycle" label="Default Cycle" />
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedServices && sortedServices.length > 0 ? (
              sortedServices.map((service) => (
                <TableRow key={service.id}>
                  <TableCell className="font-medium">{service.name}</TableCell>
                  <TableCell>{service.category || '-'}</TableCell>
                  <TableCell>${parseFloat(service.default_amount).toFixed(2)}</TableCell>
                  <TableCell>{service.default_cycle}</TableCell>
                  <TableCell>
                    <Button size="sm" variant="ghost" onClick={() => handleEditClick(service)}>
                      Edit
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan="5" className="text-center py-8 text-gray-500">
                  No services found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </Layout>
  );
}
