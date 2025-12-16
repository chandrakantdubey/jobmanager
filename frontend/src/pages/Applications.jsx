import { useState, useEffect } from 'react';
import { ExternalLink, Trash2, Search, Filter, ChevronLeft, ChevronRight, Calendar, MapPin, Briefcase } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api';
import ConfirmationModal from '../components/ConfirmationModal';

const STATUS_OPTIONS = [
    { value: 'Saved', label: 'Saved', color: 'bg-gray-100 text-gray-800' },
    { value: 'Applied', label: 'Applied', color: 'bg-blue-100 text-blue-800' },
    { value: 'Interviewing', label: 'Interviewing', color: 'bg-purple-100 text-purple-800' },
    { value: 'Offer', label: 'Offer', color: 'bg-green-100 text-green-800' },
    { value: 'Rejected', label: 'Rejected', color: 'bg-red-100 text-red-800' }
];

export default function Applications() {
    const [jobs, setJobs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [statusFilter, setStatusFilter] = useState('All');
    const [currentPage, setCurrentPage] = useState(1);
    const itemsPerPage = 8;

    // Modal State
    const [deleteModal, setDeleteModal] = useState({ show: false, jobId: null });
    const [deleteAllModal, setDeleteAllModal] = useState(false);


    useEffect(() => {
        fetchTrackedJobs();
    }, []);

    const fetchTrackedJobs = async () => {
        try {
            const res = await api.get('/tracking');
            // Sort by most recently updated/created by default
            const sorted = res.data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
            setJobs(sorted);
        } catch (err) {
            console.error(err);
            toast.error("Failed to load applications");
        } finally {
            setLoading(false);
        }
    };

    const updateStatus = async (jobId, newStatus) => {
        const oldJobs = [...jobs];
        setJobs(jobs.map(j => j.job_id === jobId ? { ...j, status: newStatus } : j));

        try {
            await api.post(`/jobs/${jobId}/track`, { status: newStatus });
            toast.success(`Status updated to ${newStatus}`);
        } catch (err) {
            console.error(err);
            setJobs(oldJobs);
            toast.error("Failed to update status");
        }
    };

    const handleDeleteClick = (userJobId) => {
        setDeleteModal({ show: true, jobId: userJobId });
    };

    const confirmDelete = async () => {
        const id = deleteModal.jobId;
        try {
            await api.delete(`/tracking/${id}`);
            setJobs(jobs.filter(j => j.id !== id));
            toast.success("Job removed from tracking");
        } catch (err) {
            console.error(err);
            toast.error("Failed to remove job");
        } finally {
            setDeleteModal({ show: false, jobId: null });
        }
    };

    const confirmDeleteAll = async () => {
        try {
            await api.delete('/tracking/all/delete');
            setJobs([]);
            toast.success("All applications removed");
        } catch (err) {
            console.error(err);
            toast.error("Failed to remove all jobs");
        } finally {
            setDeleteAllModal(false);
        }
    };

    // Filter Logic
    const filteredJobs = jobs.filter(item => {
        const matchesSearch = item.job.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
            item.job.company.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesStatus = statusFilter === 'All' || item.status === statusFilter;
        return matchesSearch && matchesStatus;
    });

    // Pagination Logic
    const totalPages = Math.ceil(filteredJobs.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const paginatedJobs = filteredJobs.slice(startIndex, startIndex + itemsPerPage);

    const getStatusColor = (status) => {
        return STATUS_OPTIONS.find(o => o.value === status)?.color || 'bg-gray-100';
    };

    if (loading) return (
        <div className="flex justify-center items-center h-full">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
    );

    return (
        <div className="max-w-7xl mx-auto">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold">Saved Jobs ({filteredJobs.length})</h2>
                {jobs.length > 0 && (
                    <button
                        onClick={() => setDeleteAllModal(true)}
                        className="flex items-center gap-2 px-3 py-2 bg-red-100 text-red-700 hover:bg-red-200 rounded-lg text-sm font-medium transition-colors border border-red-200"
                    >
                        <Trash2 size={16} />
                        Delete All
                    </button>
                )}
            </div>

            {/* Filters */}
            <div className="bg-white p-4 rounded-xl shadow-sm border mb-6 flex flex-col md:flex-row gap-4 justify-between items-center">
                <div className="relative w-full md:w-96">
                    <Search className="absolute left-3 top-2.5 text-gray-400" size={20} />
                    <input
                        type="text"
                        placeholder="Search by title or company..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                </div>

                <div className="flex items-center gap-2 w-full md:w-auto">
                    <Filter className="text-gray-400" size={20} />
                    <select
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value)}
                        className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none w-full md:w-48"
                    >
                        <option value="All">All Statuses</option>
                        {STATUS_OPTIONS.map(opt => (
                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Table */}
            <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-gray-50 border-b text-sm font-semibold text-gray-600 uppercase tracking-wider">
                                <th className="px-6 py-4">Job Info</th>
                                <th className="px-6 py-4">Location</th>
                                <th className="px-6 py-4">Date Saved</th>
                                <th className="px-6 py-4">Status</th>
                                <th className="px-6 py-4 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {paginatedJobs.length > 0 ? (
                                paginatedJobs.map(item => (
                                    <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                                        <td className="px-6 py-4">
                                            <div className="flex flex-col">
                                                <span className="font-semibold text-gray-900">{item.job.title}</span>
                                                <span className="text-sm text-gray-500 flex items-center gap-1">
                                                    <Briefcase size={12} /> {item.job.company}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-sm text-gray-600">
                                            <div className="flex items-center gap-1">
                                                <MapPin size={14} className="text-gray-400" />
                                                {item.job.location}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-sm text-gray-600">
                                            <div className="flex items-center gap-1">
                                                <Calendar size={14} className="text-gray-400" />
                                                {new Date(item.created_at).toLocaleDateString()}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <select
                                                value={item.status}
                                                onChange={(e) => updateStatus(item.job_id, e.target.value)}
                                                className={`text-xs font-semibold px-3 py-1 rounded-full border-0 outline-none cursor-pointer appearance-none ${getStatusColor(item.status)}`}
                                                style={{ WebkitAppearance: 'none', textAlign: 'center' }}
                                            >
                                                {STATUS_OPTIONS.map(opt => (
                                                    <option key={opt.value} value={opt.value}>
                                                        {opt.label}
                                                    </option>
                                                ))}
                                            </select>
                                        </td>
                                        <td className="px-6 py-4 text-right space-x-2">
                                            <a
                                                href={item.job.job_url}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors"
                                                title="View Job"
                                            >
                                                <ExternalLink size={16} />
                                            </a>
                                            <button
                                                onClick={() => handleDeleteClick(item.id)}
                                                className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
                                                title="Remove"
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            ) : (
                                <tr>
                                    <td colSpan="5" className="px-6 py-12 text-center text-gray-500">
                                        No jobs found matching your filters.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Pagination */}
                {filteredJobs.length > 0 && (
                    <div className="px-6 py-4 border-t flex justify-between items-center bg-gray-50">
                        <span className="text-sm text-gray-500">
                            Showing {startIndex + 1} to {Math.min(startIndex + itemsPerPage, filteredJobs.length)} of {filteredJobs.length} results
                        </span>
                        <div className="flex gap-2">
                            <button
                                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                disabled={currentPage === 1}
                                className="p-2 border rounded-lg hover:bg-white disabled:opacity-50 disabled:hover:bg-transparent"
                            >
                                <ChevronLeft size={16} />
                            </button>
                            <button
                                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                                disabled={currentPage === totalPages}
                                className="p-2 border rounded-lg hover:bg-white disabled:opacity-50 disabled:hover:bg-transparent"
                            >
                                <ChevronRight size={16} />
                            </button>
                        </div>
                    </div>
                )}
            </div>

            <ConfirmationModal
                isOpen={deleteModal.show}
                onClose={() => setDeleteModal({ show: false, jobId: null })}
                onConfirm={confirmDelete}
                title="Remove Job Application"
                message="Are you sure you want to remove this job from your applications? This action cannot be undone."
                confirmText="Remove Job"
                isDanger={true}
            />

            <ConfirmationModal
                isOpen={deleteAllModal}
                onClose={() => setDeleteAllModal(false)}
                onConfirm={confirmDeleteAll}
                title="Clear All Applications"
                message="Are you sure you want to remove ALL jobs from your applications? This action cannot be undone."
                confirmText="Clear All"
                isDanger={true}
            />
        </div>
    );
}
