import { useState, useEffect } from 'react';
import { ExternalLink, Calendar, Briefcase, MapPin, Search, Trash2, Target, FileText, Download, Filter } from 'lucide-react';
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
    const [siteFilter, setSiteFilter] = useState(''); // NEW: Site filter
    const [dateFrom, setDateFrom] = useState(''); // NEW: Date range from
    const [dateTo, setDateTo] = useState(''); // NEW: Date range to
    const [processing, setProcessing] = useState(null);

    // NEW: View toggle
    const [view, setView] = useState('all'); // 'all' or 'tracked'
    const [trackedJobs, setTrackedJobs] = useState([]);
    const [trackedTotal, setTrackedTotal] = useState(0);

    // Modal State
    const [deleteModal, setDeleteModal] = useState({ show: false, jobId: null });
    const [deleteAllModal, setDeleteAllModal] = useState(false);
    const [statusModal, setStatusModal] = useState({ show: false, userJobId: null, currentStatus: null });

    // Debounce search
    useEffect(() => {
        const timer = setTimeout(() => {
            if (view === 'all') {
                fetchJobs();
            } else {
                fetchTrackedJobs();
            }
        }, 500);
        return () => clearTimeout(timer);
    }, [page, search, locationFilter, siteFilter, dateFrom, dateTo, view]);

    const fetchJobs = async () => {
        setLoading(true);
        try {
            const page_size = 20;
            const query = new URLSearchParams({
                page: page + 1,
                page_size,
                ...(search && { search }),
                ...(locationFilter && { location: locationFilter }),
                ...(siteFilter && { site: siteFilter }),
                ...(dateFrom && { date_from: dateFrom }),
                ...(dateTo && { date_to: dateTo })
            });
            const res = await api.get(`/jobs?${query.toString()}`);
            if (Array.isArray(res.data)) {
                setJobs(res.data);
                setTotal(res.data.length);
            } else {
                setJobs(res.data.items || []);
                setTotal(res.data.total || 0);
            }
        } catch (err) {
            console.error(err);
            toast.error("Failed to load jobs");
        } finally {
            setLoading(false);
        }
    };

    const fetchTrackedJobs = async () => {
        setLoading(true);
        try {
            const res = await api.get('/tracking');
            // Backend returns array of UserJob objects with job details
            setTrackedJobs(res.data || []);
            setTrackedTotal(res.data?.length || 0);
        } catch (err) {
            console.error(err);
            toast.error("Failed to load tracked jobs");
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
            fetchJobs();
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

    const handleTrack = async (job, status = 'Saved') => {
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
            await api.post(`/jobs/track?status=${status}`, payload);
            toast.success(`Job tracked as ${status}`);
            if (view === 'tracked') fetchTrackedJobs();
        } catch (err) {
            console.error(err);
            toast.error("Failed to track job");
        } finally {
            setProcessing(null);
        }
    };

    const handleStatusChange = async (userJobId, newStatus) => {
        setProcessing(userJobId);
        try {
            await api.put(`/tracking/${userJobId}`, { status: newStatus });
            toast.success(`Status updated to ${newStatus}`);
            fetchTrackedJobs();
        } catch (err) {
            console.error(err);
            toast.error("Failed to update status");
        } finally {
            setProcessing(null);
            setStatusModal({ show: false, userJobId: null, currentStatus: null });
        }
    };

    const handleUntrack = async (userJobId) => {
        setProcessing(userJobId);
        try {
            await api.delete(`/tracking/${userJobId}`);
            toast.success("Job untracked");
            fetchTrackedJobs();
        } catch (err) {
            console.error(err);
            toast.error("Failed to untrack job");
        } finally {
            setProcessing(null);
        }
    };

    const exportToCSV = () => {
        const dataToExport = view === 'all' ? jobs : trackedJobs.map(uj => uj.job);
        if (dataToExport.length === 0) {
            toast.error("No data to export");
            return;
        }

        const headers = ['Title', 'Company', 'Location', 'Site', 'Date Posted', 'URL'];
        if (view === 'tracked') headers.push('Status');

        const csvContent = [
            headers.join(','),
            ...dataToExport.map((job, idx) => {
                const row = [
                    `"${(job?.title || '').replace(/"/g, '""')}"`,
                    `"${(job?.company || '').replace(/"/g, '""')}"`,
                    `"${(job?.location || '').replace(/"/g, '""')}"`,
                    `"${(job?.site || '').replace(/"/g, '""')}"`,
                    `"${job?.date_posted || ''}"`,
                    `"${job?.job_url || ''}"`
                ];
                if (view === 'tracked') {
                    row.push(`"${trackedJobs[idx]?.status || 'Saved'}"`);
                }
                return row.join(',');
            })
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `jobs_${view}_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
        toast.success(`Exported ${dataToExport.length} jobs to CSV`);
    };

    const limit = 20;
    const totalPages = Math.ceil((view === 'all' ? total : trackedTotal) / limit);

    const statusColors = {
        'Saved': 'bg-gray-100 text-gray-800',
        'Applied': 'bg-blue-100 text-blue-800',
        'Interviewing': 'bg-yellow-100 text-yellow-800',
        'Offer': 'bg-green-100 text-green-800',
        'Rejected': 'bg-red-100 text-red-800'
    };

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            {/* Header with View Toggle */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
                <div>
                    <h2 className="text-2xl font-bold text-gray-800">Job Manager</h2>
                    <p className="text-sm text-gray-500 mt-1">Browse all jobs or manage your tracked applications</p>
                </div>

                <div className="flex gap-2">
                    {/* Export Button */}
                    <button
                        onClick={exportToCSV}
                        disabled={(view === 'all' ? jobs.length : trackedJobs.length) === 0}
                        className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-sm font-medium transition-colors"
                    >
                        <Download size={16} />
                        Export CSV
                    </button>

                    {/* View Toggle Tabs */}
                    <div className="flex bg-gray-100 rounded-lg p-1">
                        <button
                            onClick={() => { setView('all'); setPage(0); }}
                            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${view === 'all' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'}`}
                        >
                            <span className="flex items-center gap-2">
                                <Briefcase size={16} />
                                All Jobs ({total})
                            </span>
                        </button>
                        <button
                            onClick={() => { setView('tracked'); setPage(0); }}
                            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${view === 'tracked' ? 'bg-white text-green-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'}`}
                        >
                            <span className="flex items-center gap-2">
                                <Target size={16} />
                                Tracked ({trackedTotal})
                            </span>
                        </button>
                    </div>
                </div>
            </div>

            {/* Filters (only for All Jobs view) */}
            {view === 'all' && (
                <div className="bg-white rounded-xl shadow-sm border p-4 mb-6">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                            <Filter size={18} className="text-gray-600" />
                            <span className="text-sm font-semibold text-gray-700">Filters</span>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                            <input
                                type="text"
                                placeholder="Search jobs, companies..."
                                value={search}
                                onChange={(e) => { setSearch(e.target.value); setPage(0); }}
                                className="w-full pl-9 pr-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                            />
                        </div>
                        <div className="relative">
                            <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                            <input
                                type="text"
                                placeholder="Location..."
                                value={locationFilter}
                                onChange={(e) => { setLocationFilter(e.target.value); setPage(0); }}
                                className="w-full pl-9 pr-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                            />
                        </div>
                        <select
                            value={siteFilter}
                            onChange={(e) => { setSiteFilter(e.target.value); setPage(0); }}
                            className="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                        >
                            <option value="">All Sites</option>
                            <option value="linkedin">LinkedIn</option>
                            <option value="indeed">Indeed</option>
                            <option value="glassdoor">Glassdoor</option>
                            <option value="ziprecruiter">ZipRecruiter</option>
                            <option value="remotive">Remotive</option>
                            <option value="himalayas">Himalayas</option>
                            <option value="weworkremotely">WeWorkRemotely</option>
                            <option value="builtin">BuiltIn</option>
                            <option value="arc">Arc.dev</option>
                            <option value="peopleperhour">PeoplePerHour</option>
                            <option value="guru">Guru</option>
                            <option value="truelancer">Truelancer</option>
                        </select>
                        <input
                            type="date"
                            value={dateFrom}
                            onChange={(e) => { setDateFrom(e.target.value); setPage(0); }}
                            placeholder="From Date"
                            className="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                        />
                        <input
                            type="date"
                            value={dateTo}
                            onChange={(e) => { setDateTo(e.target.value); setPage(0); }}
                            placeholder="To Date"
                            className="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                        />
                    </div>

                    {jobs.length > 0 && (
                        <div className="pt-4 border-t flex justify-end">
                            <button
                                onClick={() => setDeleteAllModal(true)}
                                className="flex items-center gap-2 px-3 py-2 bg-red-100 text-red-700 hover:bg-red-200 rounded-lg text-sm font-medium transition-colors border border-red-200"
                            >
                                <Trash2 size={16} />
                                Delete All Jobs
                            </button>
                        </div>
                    )}
                </div>
            )}

            {/* Pagination */}
            <div className="mb-4 flex flex-col sm:flex-row justify-between items-center gap-4">
                <p className="text-sm text-gray-500">
                    {view === 'all' ? (
                        `Showing ${jobs.length > 0 ? page * limit + 1 : 0} - ${Math.min((page + 1) * limit, total)} of ${total} jobs`
                    ) : (
                        `Showing ${trackedJobs.length} tracked jobs`
                    )}
                </p>
                {view === 'all' && totalPages > 1 && (
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
                )}
            </div>

            {/* Jobs Table */}
            {loading && (view === 'all' ? jobs.length === 0 : trackedJobs.length === 0) ? (
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
                                    {view === 'tracked' && (
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                    )}
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {view === 'all' ? (
                                    // ALL JOBS VIEW
                                    jobs.length === 0 ? (
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
                                                            onClick={() => handleTrack(job, 'Saved')}
                                                            disabled={processing === job.id}
                                                            className="p-1.5 text-green-600 hover:bg-green-50 rounded"
                                                            title="Track this job"
                                                        >
                                                            <Target size={16} />
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
                                    )
                                ) : (
                                    // TRACKED JOBS VIEW
                                    trackedJobs.length === 0 ? (
                                        <tr>
                                            <td colSpan="6" className="px-6 py-12 text-center text-gray-500">
                                                No tracked jobs yet. Track jobs from the "All Jobs" tab.
                                            </td>
                                        </tr>
                                    ) : (
                                        trackedJobs.map((userJob) => (
                                            <tr key={userJob.id} className="hover:bg-gray-50 transition-colors">
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <div className="text-sm font-medium text-gray-900 truncate max-w-xs cursor-help" title={userJob.job?.title}>
                                                        {userJob.job?.title || 'N/A'}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <div className="text-sm text-gray-500 flex items-center gap-1">
                                                        <Briefcase size={14} className="text-gray-400" />
                                                        {userJob.job?.company || 'N/A'}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <div className="text-sm text-gray-500 truncate max-w-xs">{userJob.job?.location || 'N/A'}</div>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <select
                                                        value={userJob.status}
                                                        onChange={(e) => handleStatusChange(userJob.id, e.target.value)}
                                                        disabled={processing === userJob.id}
                                                        className={`text - xs px - 3 py - 1.5 rounded - full font - medium cursor - pointer border - 0 ${statusColors[userJob.status] || 'bg-gray-100 text-gray-800'} `}
                                                    >
                                                        <option value="Saved">Saved</option>
                                                        <option value="Applied">Applied</option>
                                                        <option value="Interviewing">Interviewing</option>
                                                        <option value="Offer">Offer</option>
                                                        <option value="Rejected">Rejected</option>
                                                    </select>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                    <div className="flex items-center gap-1">
                                                        <Calendar size={14} className="text-gray-400" />
                                                        {userJob.job?.date_posted || 'N/A'}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                    <div className="flex justify-end items-center gap-2">
                                                        <a
                                                            href={userJob.job?.job_url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="p-1.5 text-blue-600 hover:bg-blue-50 rounded"
                                                            title="View on site"
                                                        >
                                                            <ExternalLink size={16} />
                                                        </a>
                                                        <button
                                                            onClick={() => handleUntrack(userJob.id)}
                                                            disabled={processing === userJob.id}
                                                            className="p-1.5 text-red-600 hover:bg-red-50 rounded"
                                                            title="Untrack this job"
                                                        >
                                                            <Trash2 size={16} />
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))
                                    )
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
