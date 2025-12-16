import { useState, useEffect } from 'react';
import { ExternalLink, Calendar, Briefcase, MapPin, Search, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api';
import ConfirmationModal from '../components/ConfirmationModal';

export default function ScrapedJobs() {
    const [jobs, setJobs] = useState([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(0);
    const [search, setSearch] = useState('');
    const [locationFilter, setLocationFilter] = useState('');
    const [processing, setProcessing] = useState(null); // ID of job being processed

    // Modal State
    const [deleteModal, setDeleteModal] = useState({ show: false, jobId: null });
    const [deleteAllModal, setDeleteAllModal] = useState(false);

    // Debounce search
    useEffect(() => {
        const timer = setTimeout(() => {
            fetchJobs();
        }, 500);
        return () => clearTimeout(timer);
    }, [page, search, locationFilter]);

    const fetchJobs = async () => {
        setLoading(true);
        try {
            const limit = 20;
            const offset = page * limit;
            const query = new URLSearchParams({
                limit,
                offset,
                search,
                location: locationFilter
            });
            const res = await api.get(`/jobs?${query.toString()}`);
            // Backward compatibility check if backend returns array or object
            if (Array.isArray(res.data)) {
                setJobs(res.data);
                setTotal(res.data.length); // Fallback
            } else {
                setJobs(res.data.items);
                setTotal(res.data.total);
            }
        } catch (err) {
            console.error(err);
            toast.error("Failed to load jobs");
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteClick = (id) => {
        setDeleteModal({ show: true, jobId: id });
    };

    const confirmDelete = async () => {
        const id = deleteModal.jobId;
        setProcessing(id);
        try {
            await api.delete(`/jobs/${id}`);
            toast.success("Job deleted successfully");
            fetchJobs(); // Refresh
        } catch (err) {
            console.error(err);
            toast.error("Failed to delete job");
        } finally {
            setProcessing(null);
            setDeleteModal({ show: false, jobId: null });
        }
    };

    const confirmDeleteAll = async () => {
        try {
            await api.delete('/jobs/all/delete');
            toast.success("All scraped jobs deleted");
            setPage(0);
            fetchJobs();
        } catch (err) {
            console.error(err);
            toast.error("Failed to delete all jobs");
        } finally {
            setDeleteAllModal(false);
        }
    };

    const handleTrack = async (job) => {
        setProcessing(job.id);
        try {
            const payload = {
                title: job.title,
                company: job.company,
                location: job.location,
                job_url: job.job_url,
                description: job.description || "",
                site: job.site,
                date_posted: job.date_posted,
                match_score: job.match_score || 0
            };
            await api.post(`/jobs/track?status=Applied`, payload);
            toast.success("Job moved to Applications");
        } catch (err) {
            console.error(err);
            toast.error("Failed to move job");
        } finally {
            setProcessing(null);
        }
    };

    const limit = 20;
    const totalPages = Math.ceil(total / limit);

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
                <h2 className="text-2xl font-bold text-gray-800">Global Scraped Jobs</h2>
                <div className="flex flex-wrap gap-2 w-full md:w-auto items-center">
                    <div className="relative flex-1 md:w-64">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                        <input
                            type="text"
                            placeholder="Search jobs, companies..."
                            value={search}
                            onChange={(e) => { setSearch(e.target.value); setPage(0); }}
                            className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                        />
                    </div>
                    <div className="relative flex-1 md:w-48">
                        <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                        <input
                            type="text"
                            placeholder="Location..."
                            value={locationFilter}
                            onChange={(e) => { setLocationFilter(e.target.value); setPage(0); }}
                            className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                        />
                    </div>
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
            </div>

            <div className="mb-4 flex flex-col sm:flex-row justify-between items-center gap-4">
                <p className="text-sm text-gray-500">
                    Showing {jobs.length > 0 ? page * limit + 1 : 0} - {Math.min((page + 1) * limit, total)} of {total} jobs
                </p>
                <div className="flex gap-2 items-center">
                    <button
                        onClick={() => setPage(Math.max(0, page - 1))}
                        disabled={page === 0}
                        className="px-4 py-2 border bg-white rounded-lg disabled:opacity-50 hover:bg-gray-50 text-sm font-medium"
                    >
                        Previous
                    </button>
                    <span className="text-sm text-gray-600">Page {page + 1} of {totalPages || 1}</span>
                    <button
                        onClick={() => setPage(page + 1)}
                        disabled={page >= totalPages - 1}
                        className="px-4 py-2 border bg-white rounded-lg disabled:opacity-50 hover:bg-gray-50 text-sm font-medium"
                    >
                        Next
                    </button>
                </div>
            </div>

            {loading && jobs.length === 0 ? (
                <div className="flex justify-center items-center py-20">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
            ) : (
                <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Job Title</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Company</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Location</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date Posted</th>
                                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {jobs.length === 0 ? (
                                    <tr>
                                        <td colSpan="5" className="px-6 py-12 text-center text-gray-500">
                                            No jobs found matching your criteria.
                                        </td>
                                    </tr>
                                ) : (
                                    jobs.map((job) => (
                                        <tr key={job.id} className="hover:bg-gray-50 transition-colors">
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <div className="text-sm font-medium text-gray-900 truncate max-w-xs cursor-help" title={job.title}>{job.title}</div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <div className="text-sm text-gray-500 flex items-center gap-1">
                                                    <Briefcase size={14} className="text-gray-400" />
                                                    {job.company}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <div className="text-sm text-gray-500 truncate max-w-xs">{job.location}</div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                <div className="flex items-center gap-1">
                                                    <Calendar size={14} className="text-gray-400" />
                                                    {job.date_posted || 'N/A'}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                <div className="flex justify-end items-center gap-2">
                                                    <a
                                                        href={job.job_url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="p-1.5 text-blue-600 hover:bg-blue-50 rounded"
                                                        title="View on site"
                                                    >
                                                        <ExternalLink size={16} />
                                                    </a>
                                                    <button
                                                        onClick={() => handleTrack(job)}
                                                        disabled={processing === job.id}
                                                        className="p-1.5 text-green-600 hover:bg-green-50 rounded"
                                                        title="Add to Applications"
                                                    >
                                                        <Briefcase size={16} />
                                                    </button>
                                                    <button
                                                        onClick={() => handleDeleteClick(job.id)}
                                                        disabled={processing === job.id}
                                                        className="p-1.5 text-red-600 hover:bg-red-50 rounded"
                                                        title="Delete from list"
                                                    >
                                                        <Trash2 size={16} />
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            <ConfirmationModal
                isOpen={deleteModal.show}
                onClose={() => setDeleteModal({ show: false, jobId: null })}
                onConfirm={confirmDelete}
                title="Delete Scraped Job"
                message="Are you sure you want to delete this job? This action cannot be undone."
                confirmText="Delete Job"
                isDanger={true}
            />

            <ConfirmationModal
                isOpen={deleteAllModal}
                onClose={() => setDeleteAllModal(false)}
                onConfirm={confirmDeleteAll}
                title="Delete ALL Scraped Jobs"
                message="⚠ WARNING: This will delete ALL scraped jobs from the database. This includes any jobs you haven't reviewed yet. This action cannot be undone."
                confirmText="Delete EVERYTHING"
                isDanger={true}
            />
        </div>
    );
}
