import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../api/client';
import Layout from '../components/Layout';
import { Card } from '../components/ui/Card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/Table';
import Button from '../components/ui/Button';

export default function ServiceCatalogPage() {
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

  return (
    <Layout title="Service Catalog">
      <div className="mb-6">
        <Button>+ Add Service</Button>
      </div>

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Default Amount</TableHead>
              <TableHead>Default Cycle</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {services && services.length > 0 ? (
              services.map((service) => (
                <TableRow key={service.id}>
                  <TableCell className="font-medium">{service.name}</TableCell>
                  <TableCell>{service.category || '-'}</TableCell>
                  <TableCell>${parseFloat(service.default_amount).toFixed(2)}</TableCell>
                  <TableCell>{service.default_cycle}</TableCell>
                  <TableCell>
                    <Button size="sm" variant="ghost">
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
