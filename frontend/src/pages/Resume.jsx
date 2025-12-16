import { useState, useEffect } from 'react';
import { Upload, FileText, Trash2, Calendar, Settings, Edit2 } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api';
import ConfirmationModal from '../components/ConfirmationModal';
import PreferencesModal from '../components/PreferencesModal';

export default function Resume() {
    const [file, setFile] = useState(null);
    const [resumes, setResumes] = useState([]);
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);

    // Delete Modal State
    const [deleteModal, setDeleteModal] = useState({ show: false, resumeId: null });

    useEffect(() => {
        fetchResumes();
    }, []);

    const fetchResumes = async () => {
        setLoading(true);
        try {
            const res = await api.get('/resumes/');
            // Sort: active first, then by date
            const sorted = res.data.sort((a, b) => {
                if (a.is_active && !b.is_active) return -1;
                if (!a.is_active && b.is_active) return 1;
                return new Date(b.upload_date) - new Date(a.upload_date);
            });
            setResumes(sorted);
        } catch (err) {
            console.error(err);
            toast.error("Failed to load resumes");
        } finally {
            setLoading(false);
        }
    };

    const handleFileChange = (e) => {
        setFile(e.target.files[0]);
    };

    const handleUpload = async () => {
        if (!file) return;

        setUploading(true);

        const formData = new FormData();
        formData.append('file', file);

        try {
            await api.post('/resumes/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            await fetchResumes();
            setFile(null);
            document.getElementById('file-upload').value = null;
            toast.success("Resume uploaded successfully");
        } catch (err) {
            console.error(err);
            toast.error("Failed to upload resume");
        } finally {
            setUploading(false);
        }
    };

    const handleDeleteClick = (id) => {
        setDeleteModal({ show: true, resumeId: id });
    };

    const confirmDelete = async () => {
        const id = deleteModal.resumeId;
        try {
            await api.delete(`/resumes/${id}`);
            setResumes(resumes.filter(r => r.id !== id));
            toast.success("Resume deleted");
        } catch (err) {
            console.error(err);
            toast.error("Failed to delete resume");
        } finally {
            setDeleteModal({ show: false, resumeId: null });
        }
    };

    const handleActivate = async (id) => {
        try {
            await api.post(`/resumes/${id}/activate`);
            await fetchResumes();
            toast.success("Resume activated");
        } catch (err) {
            console.error(err);
            toast.error("Failed to activate resume");
        }
    };

    return (
        <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl font-bold mb-6">Resume Management</h2>

            <div className="bg-white p-6 rounded-xl shadow-sm border mb-8">
                <h3 className="text-lg font-semibold mb-4">Upload New Resume</h3>
                <div className="flex gap-4 items-end">
                    <div className="flex-1">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Select PDF File
                        </label>
                        <input
                            id="file-upload"
                            type="file"
                            accept=".pdf"
                            onChange={handleFileChange}
                            className="block w-full text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded-full file:border-0
                file:text-sm file:font-semibold
                file:bg-blue-50 file:text-blue-700
                hover:file:bg-blue-100"
                        />
                    </div>
                    <button
                        onClick={handleUpload}
                        disabled={!file || uploading}
                        className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                    >
                        {uploading ? 'Uploading...' : 'Upload'}
                        {!uploading && <Upload size={18} />}
                    </button>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                    Note: The ACTIVE resume is used for job matching.
                </p>
            </div>

            <h3 className="text-lg font-semibold mb-4">Your Resumes</h3>
            {loading ? (
                <p>Loading...</p>
            ) : (
                <div className="space-y-4">
                    {resumes.length === 0 ? (
                        <p className="text-gray-500">No resumes uploaded yet.</p>
                    ) : (
                        resumes.map((resume) => (
                            <ResumeCard key={resume.id} resume={resume} onDelete={handleDeleteClick} onActivate={handleActivate} onUpdate={fetchResumes} />
                        ))
                    )}
                </div>
            )}

            <ConfirmationModal
                isOpen={deleteModal.show}
                onClose={() => setDeleteModal({ show: false, resumeId: null })}
                onConfirm={confirmDelete}
                title="Delete Resume"
                message="Are you sure you want to delete this resume? This action cannot be undone."
                confirmText="Delete Resume"
                isDanger={true}
            />
        </div>
    );
}

function ResumeCard({ resume, onDelete, onActivate, onUpdate }) {
    // Edit Skills State
    const [editingSkills, setEditingSkills] = useState(false);
    const [skillsInput, setSkillsInput] = useState(resume.extracted_skills?.join(', ') || '');

    // Edit Titles State
    const [editingTitles, setEditingTitles] = useState(false);
    const [titlesInput, setTitlesInput] = useState(resume.parsed_titles?.join(', ') || '');

    // Preferences Modal State
    const [showPrefs, setShowPrefs] = useState(false);

    const [saving, setSaving] = useState(false);

    const handleSaveSkills = async () => {
        setSaving(true);
        try {
            const skills = skillsInput.split(',').map(s => s.trim()).filter(s => s);
            await api.put(`/resumes/${resume.id}`, { extracted_skills: skills });
            setEditingSkills(false);
            onUpdate();
            toast.success("Skills updated");
        } catch (err) {
            console.error(err);
            toast.error("Failed to update skills");
        } finally {
            setSaving(false);
        }
    };

    const handleSaveTitles = async () => {
        setSaving(true);
        try {
            const titles = titlesInput.split(',').map(s => s.trim()).filter(s => s);
            await api.put(`/resumes/${resume.id}`, { parsed_titles: titles });
            setEditingTitles(false);
            onUpdate();
            toast.success("Titles updated");
        } catch (err) {
            console.error(err);
            toast.error("Failed to update titles");
        } finally {
            setSaving(false);
        }
    };

    const handleSavePrefs = async (newPrefs) => {
        try {
            await api.put(`/resumes/${resume.id}`, { search_preferences: newPrefs });
            onUpdate();
            toast.success("Preferences saved");
        } catch (err) {
            console.error(err);
            toast.error("Failed to save preferences");
        }
    };

    return (
        <div className={`bg-white p-6 rounded-xl shadow-sm border ${resume.is_active ? 'border-green-500 ring-1 ring-green-500' : ''}`}>
            <div className="flex justify-between items-start">
                <div className="flex items-center gap-3">
                    <div className={`p-3 rounded-full ${resume.is_active ? 'bg-green-100' : 'bg-gray-100'}`}>
                        <FileText className={resume.is_active ? 'text-green-600' : 'text-gray-600'} size={24} />
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <h3 className="text-lg font-semibold">{resume.filename}</h3>
                            {resume.is_active && (
                                <span className="bg-green-100 text-green-800 text-xs px-2 py-0.5 rounded-full font-medium">
                                    Active
                                </span>
                            )}
                        </div>
                        <p className="text-sm text-gray-500 flex items-center gap-1">
                            <Calendar size={12} />
                            Uploaded on {new Date(resume.upload_date).toLocaleString()}
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setShowPrefs(true)}
                        className="text-xs bg-gray-100 text-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-200 font-medium flex items-center gap-1"
                    >
                        <Settings size={14} /> Options
                    </button>

                    {!resume.is_active && (
                        <button
                            onClick={() => onActivate(resume.id)}
                            className="text-xs bg-blue-100 text-blue-700 px-3 py-1.5 rounded-lg hover:bg-blue-200 font-medium"
                        >
                            Make Active
                        </button>
                    )}
                    <button
                        onClick={() => onDelete(resume.id)}
                        className="text-gray-400 hover:text-red-500 transition-colors p-2"
                        title="Delete"
                    >
                        <Trash2 size={18} />
                    </button>
                </div>
            </div>

            <div className="mt-4 pl-14 space-y-4">
                {/* Titles Section */}
                <div>
                    <div className="flex justify-between items-end mb-2">
                        <h4 className="text-sm font-medium text-blue-900">Extracted Titles (Jobs you are looking for)</h4>
                        {!editingTitles && (
                            <button onClick={() => setEditingTitles(true)} className="text-xs text-blue-600 hover:underline flex items-center gap-1">
                                <Edit2 size={10} /> Edit Titles
                            </button>
                        )}
                    </div>
                    {editingTitles ? (
                        <div className="space-y-2">
                            <textarea
                                value={titlesInput}
                                onChange={(e) => setTitlesInput(e.target.value)}
                                className="w-full text-sm p-2 border rounded-md"
                                rows={2}
                                placeholder="Comma separated titles (e.g. Python Developer, Backend Engineer)..."
                            />
                            <div className="flex gap-2">
                                <button
                                    onClick={handleSaveTitles}
                                    disabled={saving}
                                    className="text-xs bg-blue-600 text-white px-3 py-1 rounded"
                                >
                                    {saving ? 'Saving...' : 'Save'}
                                </button>
                                <button
                                    onClick={() => setEditingTitles(false)}
                                    className="text-xs bg-gray-200 text-gray-700 px-3 py-1 rounded"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="flex flex-wrap gap-2">
                            {resume.parsed_titles && resume.parsed_titles.length > 0 ? (
                                resume.parsed_titles.map((title, i) => (
                                    <span
                                        key={i}
                                        className="px-2 py-1 bg-blue-50 text-blue-700 rounded-md text-xs border border-blue-100"
                                    >
                                        {title}
                                    </span>
                                ))
                            ) : (
                                <span className="text-sm text-gray-400 italic">No job titles detected. Click edit to add.</span>
                            )}
                        </div>
                    )}
                </div>

                {/* Skills Section */}
                <div>
                    <div className="flex justify-between items-end mb-2">
                        <h4 className="text-sm font-medium text-gray-700">Extracted Skills</h4>
                        {!editingSkills && (
                            <button onClick={() => setEditingSkills(true)} className="text-xs text-blue-600 hover:underline flex items-center gap-1">
                                <Edit2 size={10} /> Edit Skills
                            </button>
                        )}
                    </div>

                    {editingSkills ? (
                        <div className="space-y-2">
                            <textarea
                                value={skillsInput}
                                onChange={(e) => setSkillsInput(e.target.value)}
                                className="w-full text-sm p-2 border rounded-md"
                                rows={3}
                                placeholder="Comma separated skills..."
                            />
                            <div className="flex gap-2">
                                <button
                                    onClick={handleSaveSkills}
                                    disabled={saving}
                                    className="text-xs bg-blue-600 text-white px-3 py-1 rounded"
                                >
                                    {saving ? 'Saving...' : 'Save'}
                                </button>
                                <button
                                    onClick={() => setEditingSkills(false)}
                                    className="text-xs bg-gray-200 text-gray-700 px-3 py-1 rounded"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="flex flex-wrap gap-2">
                            {resume.extracted_skills && resume.extracted_skills.length > 0 ? (
                                resume.extracted_skills.map((skill, i) => (
                                    <span
                                        key={i}
                                        className="px-2 py-1 bg-gray-50 text-gray-700 rounded-md text-xs border"
                                    >
                                        {skill}
                                    </span>
                                ))
                            ) : (
                                <span className="text-sm text-gray-400 italic">No skills extracted.</span>
                            )}
                        </div>
                    )}
                </div>
            </div>

            <PreferencesModal
                isOpen={showPrefs}
                onClose={() => setShowPrefs(false)}
                onSave={handleSavePrefs}
                initialPreferences={resume.search_preferences}
            />
        </div>
    );
}


