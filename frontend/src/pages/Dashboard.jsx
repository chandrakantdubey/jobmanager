import { useEffect, useState, useContext } from 'react';
import { Link } from 'react-router-dom';
import { Database, Target, FileText, ArrowRight, Upload, Edit2, Save, X } from 'lucide-react';
import api from '../api';
import { AuthContext } from '../context/AuthContext';
import toast from 'react-hot-toast';

export default function Dashboard() {
    const { token } = useContext(AuthContext);
    const [stats, setStats] = useState({
        totalJobs: 0,
        trackedJobs: 0,
        activeResume: null
    });
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [editing, setEditing] = useState(false);
    const [editedSkills, setEditedSkills] = useState([]);
    const [editedTitles, setEditedTitles] = useState([]);
    const [newSkill, setNewSkill] = useState('');
    const [newTitle, setNewTitle] = useState('');

    const fetchStats = async () => {
        try {
            // Fetch total scraped jobs
            const jobsRes = await api.get('/jobs?page=1&page_size=1');
            const totalJobs = jobsRes.data.total || 0;

            // Fetch tracked jobs
            const trackingRes = await api.get('/tracking');
            const trackedJobs = trackingRes.data?.length || 0;

            // Fetch active resume
            let activeResume = null;
            try {
                const resumeRes = await api.get('/resumes/active');
                activeResume = resumeRes.data;
            } catch (err) {
                // No active resume
            }

            setStats({ totalJobs, trackedJobs, activeResume });
            setLoading(false);
        } catch (err) {
            console.error('Error fetching stats:', err);
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStats();
    }, []);

    const handleFileUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        if (file.type !== 'application/pdf') {
            toast.error('Please upload a PDF file');
            return;
        }

        setUploading(true);
        const formData = new FormData();
        formData.append('file', file);

        try {
            await api.post('/resumes/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            toast.success('Resume uploaded successfully!');
            fetchStats();
        } catch (err) {
            console.error(err);
            toast.error('Failed to upload resume');
        } finally {
            setUploading(false);
            e.target.value = ''; // Reset input
        }
    };

    const startEditing = () => {
        setEditedSkills([...(stats.activeResume?.extracted_skills || [])]);
        setEditedTitles([...(stats.activeResume?.parsed_titles || [])]);
        setEditing(true);
    };

    const cancelEditing = () => {
        setEditing(false);
        setNewSkill('');
        setNewTitle('');
    };

    const saveEdits = async () => {
        try {
            await api.put(`/resumes/${stats.activeResume.id}`, {
                extracted_skills: editedSkills,
                parsed_titles: editedTitles
            });
            toast.success('Resume updated successfully!');
            setEditing(false);
            fetchStats();
        } catch (err) {
            console.error(err);
            toast.error('Failed to update resume');
        }
    };

    const addSkill = () => {
        if (newSkill.trim()) {
            setEditedSkills([...editedSkills, newSkill.trim()]);
            setNewSkill('');
        }
    };

    const removeSkill = (index) => {
        setEditedSkills(editedSkills.filter((_, i) => i !== index));
    };

    const addTitle = () => {
        if (newTitle.trim()) {
            setEditedTitles([...editedTitles, newTitle.trim()]);
            setNewTitle('');
        }
    };

    const removeTitle = (index) => {
        setEditedTitles(editedTitles.filter((_, i) => i !== index));
    };

    return (
        <div className="max-w-6xl mx-auto">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900 mb-2">
                    Dashboard
                </h1>
                <p className="text-gray-600">
                    Search, scrape, and track job opportunities from 29 platforms
                </p>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-white rounded-xl shadow-sm border p-6">
                    <div className="flex items-center justify-between mb-4">
                        <div className="p-3 bg-blue-100 rounded-lg">
                            <Database className="text-blue-600" size={24} />
                        </div>
                    </div>
                    <div className="text-3xl font-bold text-gray-900 mb-1">
                        {loading ? '...' : stats.totalJobs.toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-500">Total Scraped Jobs</div>
                </div>

                <div className="bg-white rounded-xl shadow-sm border p-6">
                    <div className="flex items-center justify-between mb-4">
                        <div className="p-3 bg-green-100 rounded-lg">
                            <Target className="text-green-600" size={24} />
                        </div>
                    </div>
                    <div className="text-3xl font-bold text-gray-900 mb-1">
                        {loading ? '...' : stats.trackedJobs}
                    </div>
                    <div className="text-sm text-gray-500">Tracked Jobs</div>
                </div>

                <div className="bg-white rounded-xl shadow-sm border p-6">
                    <div className="flex items-center justify-between mb-4">
                        <div className="p-3 bg-purple-100 rounded-lg">
                            <FileText className="text-purple-600" size={24} />
                        </div>
                    </div>
                    <div className="text-lg font-semibold text-gray-900 mb-1 truncate">
                        {loading ? '...' : (stats.activeResume?.filename || 'No Resume')}
                    </div>
                    <div className="text-sm text-gray-500">Active Resume</div>
                </div>
            </div>

            {/* Resume Upload & Editor Section */}
            <div className="bg-white rounded-xl shadow-sm border p-6 mb-8">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h2 className="text-xl font-semibold text-gray-900">Resume Management</h2>
                        <p className="text-sm text-gray-500 mt-1">Upload and customize your resume details</p>
                    </div>
                    {stats.activeResume && !editing && (
                        <button
                            onClick={startEditing}
                            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
                        >
                            <Edit2 size={16} />
                            Edit Skills & Titles
                        </button>
                    )}
                    {editing && (
                        <div className="flex gap-2">
                            <button
                                onClick={saveEdits}
                                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium"
                            >
                                <Save size={16} />
                                Save Changes
                            </button>
                            <button
                                onClick={cancelEditing}
                                className="flex items-center gap-2 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm font-medium"
                            >
                                <X size={16} />
                                Cancel
                            </button>
                        </div>
                    )}
                </div>

                {/* Upload Section */}
                <div className="mb-6">
                    <label className="block mb-2">
                        <span className="text-sm font-medium text-gray-700">Upload Resume (PDF)</span>
                        <div className="mt-2 flex items-center gap-4">
                            <label className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 cursor-pointer text-sm font-medium">
                                <Upload size={16} />
                                {uploading ? 'Uploading...' : 'Choose File'}
                                <input
                                    type="file"
                                    accept=".pdf"
                                    onChange={handleFileUpload}
                                    disabled={uploading}
                                    className="hidden"
                                />
                            </label>
                            <span className="text-sm text-gray-500">
                                {stats.activeResume ? `Current: ${stats.activeResume.filename}` : 'No resume uploaded'}
                            </span>
                        </div>
                    </label>
                </div>

                {/* Skills & Titles Editor */}
                {stats.activeResume && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Skills */}
                        <div>
                            <h3 className="text-sm font-semibold text-gray-700 mb-3">Extracted Skills</h3>
                            <div className="space-y-2">
                                {editing ? (
                                    <>
                                        <div className="flex gap-2 mb-3">
                                            <input
                                                type="text"
                                                value={newSkill}
                                                onChange={(e) => setNewSkill(e.target.value)}
                                                onKeyPress={(e) => e.key === 'Enter' && addSkill()}
                                                placeholder="Add a skill..."
                                                className="flex-1 px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                            />
                                            <button
                                                onClick={addSkill}
                                                className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
                                            >
                                                Add
                                            </button>
                                        </div>
                                        <div className="flex flex-wrap gap-2">
                                            {editedSkills.map((skill, idx) => (
                                                <span key={idx} className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                                                    {skill}
                                                    <button onClick={() => removeSkill(idx)} className="hover:text-blue-600">
                                                        <X size={14} />
                                                    </button>
                                                </span>
                                            ))}
                                        </div>
                                    </>
                                ) : (
                                    <div className="flex flex-wrap gap-2">
                                        {stats.activeResume.extracted_skills?.map((skill, idx) => (
                                            <span key={idx} className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                                                {skill}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Titles */}
                        <div>
                            <h3 className="text-sm font-semibold text-gray-700 mb-3">Parsed Job Titles</h3>
                            <div className="space-y-2">
                                {editing ? (
                                    <>
                                        <div className="flex gap-2 mb-3">
                                            <input
                                                type="text"
                                                value={newTitle}
                                                onChange={(e) => setNewTitle(e.target.value)}
                                                onKeyPress={(e) => e.key === 'Enter' && addTitle()}
                                                placeholder="Add a job title..."
                                                className="flex-1 px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-green-500 outline-none"
                                            />
                                            <button
                                                onClick={addTitle}
                                                className="px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm"
                                            >
                                                Add
                                            </button>
                                        </div>
                                        <div className="flex flex-wrap gap-2">
                                            {editedTitles.map((title, idx) => (
                                                <span key={idx} className="inline-flex items-center gap-1 px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm">
                                                    {title}
                                                    <button onClick={() => removeTitle(idx)} className="hover:text-green-600">
                                                        <X size={14} />
                                                    </button>
                                                </span>
                                            ))}
                                        </div>
                                    </>
                                ) : (
                                    <div className="flex flex-wrap gap-2">
                                        {stats.activeResume.parsed_titles?.map((title, idx) => (
                                            <span key={idx} className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm">
                                                {title}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Link
                    to="/search"
                    className="group bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl shadow-lg hover:shadow-xl transition-all p-8 text-white"
                >
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-2xl font-bold">Start New Search</h3>
                        <ArrowRight className="group-hover:translate-x-1 transition-transform" size={24} />
                    </div>
                    <p className="text-blue-100">
                        Search and scrape jobs from 29 platforms in real-time
                    </p>
                </Link>

                <Link
                    to="/scraped"
                    className="group bg-gradient-to-br from-green-500 to-green-600 rounded-xl shadow-lg hover:shadow-xl transition-all p-8 text-white"
                >
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-2xl font-bold">View Scraped Jobs</h3>
                        <ArrowRight className="group-hover:translate-x-1 transition-transform" size={24} />
                    </div>
                    <p className="text-green-100">
                        Browse, filter, and track your scraped job listings
                    </p>
                </Link>
            </div>
        </div>
    );
}

