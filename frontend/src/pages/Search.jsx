import { useState, useContext, useRef, useEffect } from 'react';
import { Search, Briefcase, MapPin, Globe, ExternalLink, Bookmark, Check, Loader2 } from 'lucide-react';
import api from '../api';
import { AuthContext } from '../context/AuthContext';

export default function SearchPage() {
    const { token } = useContext(AuthContext);
    const [params, setParams] = useState({
        search_term: 'Python Developer',
        location: 'India',
        results_wanted: 10,
        sites: 'linkedin,indeed',
        is_remote: false,
        country: 'india',
        job_type: '',
        easy_apply: false,
        date_posted: '',
        experience: '', // New filter
    });

    const [jobs, setJobs] = useState([]);
    const [loading, setLoading] = useState(false);
    const [tracking, setTracking] = useState({});
    const [logs, setLogs] = useState([]);
    const abortControllerRef = useRef(null);

    const [activeResume, setActiveResume] = useState(null);

    // Fetch Active Resume on Mount
    useEffect(() => {
        const fetchResume = async () => {
            try {
                const res = await api.get('/resumes/active');
                setActiveResume(res.data);

                // Pre-fill search_term if empty and titles exist
                let newTerm = params.search_term;
                if (res.data.parsed_titles && res.data.parsed_titles.length > 0 && params.search_term === 'Python Developer') {
                    newTerm = res.data.parsed_titles[0];
                }

                // Apply Preferences
                let newParams = { ...params, search_term: newTerm };
                if (res.data.search_preferences && Object.keys(res.data.search_preferences).length > 0) {
                    newParams = { ...newParams, ...res.data.search_preferences };
                }
                setParams(newParams);

            } catch (err) {
                // Squelch 404s if no resume
                console.log("No active resume found or error fetching.");
            }
        };
        fetchResume();
    }, []);

    const handleSearch = async (e) => {
        e.preventDefault();
        setLoading(true);
        setLogs([]);
        setJobs([]);

        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
        abortControllerRef.current = new AbortController();

        // Build Query String
        const searchParams = new URLSearchParams();
        Object.keys(params).forEach(key => {
            // Handle comma-separated lists if needed, but for now exact logic
            if (params[key] !== '') searchParams.append(key, params[key]);
        });
        searchParams.append('token', token); // Pass token for SSE auth

        try {
            const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8001'}/search/stream?${searchParams.toString()}`, {
                signal: abortControllerRef.current.signal
            });

            if (!response.ok) throw new Error("Search failed");

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const data = JSON.parse(line);
                        if (data.type === 'update') {
                            setLogs(prev => [...prev, data.message]);
                        } else if (data.type === 'result') {
                            setJobs(data.data);
                        } else if (data.type === 'error') {
                            setLogs(prev => [...prev, `Error: ${data.message}`]);
                        }
                    } catch (e) {
                        console.error("Error parsing stream:", e);
                    }
                }
            }
        } catch (err) {
            if (err.name !== 'AbortError') {
                console.error(err);
                setLogs(prev => [...prev, "Check console for errors."]);
            }
        } finally {
            setLoading(false);
        }
    };

    const trackJob = async (job, status = 'Saved') => {
        // Use job.id as key for UI state, but backend might return a new ID if it created the job
        // If job has no ID (streamed plain object), we use job_url as temporary key or index
        const key = job.job_url;
        setTracking(prev => ({ ...prev, [key]: 'loading' }));
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
            const res = await api.post(`/jobs/track?status=${status}`, payload);
            setTracking(prev => ({ ...prev, [key]: status }));
        } catch (err) {
            console.error(err);
            setTracking(prev => ({ ...prev, [key]: 'error' }));
            alert("Failed to save job. Please try again.");
        }
    };

    const handleSaveAll = async () => {
        if (!window.confirm(`Save all ${jobs.length} visible jobs?`)) return;
        for (const job of jobs) {
            if (!tracking[job.job_url]) {
                await trackJob(job, 'Saved');
            }
        }
    };

    const addTitleToSearch = (title) => {
        // Logic: If plain text, replace. If we want multi-select, logic is different.
        // User asked "select more that one titles".
        // Let's implement OR logic: "Title1 OR Title2"
        const current = params.search_term;
        if (current.includes(title)) {
            // Remove
            const newTerm = current.replace(title, '').replace(' OR ', ' ').trim();
            // Cleanup double spaces or trailing/leading ORs is hard with regex, let's just replace
            // Simple approach: Split by ' OR ', filter, join
            const parts = current.split(' OR ').map(s => s.trim()).filter(s => s !== title);
            setParams(p => ({ ...p, search_term: parts.join(' OR ') }));
        } else {
            // Add
            if (current && !current.includes(title)) {
                setParams(p => ({ ...p, search_term: `${current} OR ${title}` }));
            } else {
                setParams(p => ({ ...p, search_term: title }));
            }
        }
    };

    return (
        <div className="max-w-6xl mx-auto">
            <h2 className="text-2xl font-bold mb-6">Find Jobs</h2>

            {/* Search Form */}
            <div className="bg-white p-6 rounded-xl shadow-sm border mb-8">
                {activeResume && (
                    <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-100">
                        <h3 className="text-sm font-semibold text-blue-900 mb-2 flex items-center gap-2">
                            <Briefcase size={16} />
                            Active Resume Context: {activeResume.filename}
                        </h3>

                        {activeResume.parsed_titles && activeResume.parsed_titles.length > 0 && (
                            <div className="mb-3">
                                <span className="text-xs text-blue-700 font-medium block mb-1">Detected Titles (Click to add to search):</span>
                                <div className="flex flex-wrap gap-2">
                                    {activeResume.parsed_titles.map((title, idx) => (
                                        <button
                                            key={idx}
                                            type="button"
                                            onClick={() => addTitleToSearch(title)}
                                            className={`px-2 py-1 text-xs rounded-full border transition-colors ${params.search_term.includes(title)
                                                ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                                                : 'bg-white text-blue-700 border-blue-200 hover:bg-blue-100'
                                                }`}
                                        >
                                            {title}
                                            {params.search_term.includes(title) && <Check size={10} className="inline ml-1" />}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {activeResume.extracted_skills && (
                            <div>
                                <span className="text-xs text-blue-700 font-medium block mb-1">Key Skills:</span>
                                <div className="flex flex-wrap gap-1">
                                    {activeResume.extracted_skills.slice(0, 10).map((skill, i) => (
                                        <span key={i} className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded">
                                            {skill}
                                        </span>
                                    ))}
                                    {activeResume.extracted_skills.length > 10 && (
                                        <span className="text-xs text-blue-500 self-center">+{activeResume.extracted_skills.length - 10} more</span>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                <form onSubmit={handleSearch} className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        <div className="lg:col-span-2">
                            <label className="block text-sm font-medium text-gray-700 mb-1">Keywords</label>
                            <input
                                type="text"
                                value={params.search_term}
                                onChange={e => setParams({ ...params, search_term: e.target.value })}
                                placeholder="e.g. Python Developer"
                                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Location <span className="text-gray-400 text-xs">(City, State, Zip)</span>
                            </label>
                            <input
                                type="text"
                                value={params.location}
                                onChange={e => setParams({ ...params, location: e.target.value })}
                                placeholder="e.g. San Francisco, CA"
                                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                            />
                        </div>
                        <div className="lg:col-span-3">
                            <label className="block text-sm font-medium text-gray-700 mb-2">Sites</label>
                            <div className="flex flex-wrap gap-3">
                                {[
                                    { id: 'linkedin', label: 'LinkedIn' },
                                    { id: 'indeed', label: 'Indeed' },
                                    { id: 'glassdoor', label: 'Glassdoor' },
                                    { id: 'zip_recruiter', label: 'ZipRecruiter' },
                                    { id: 'google', label: 'Google (Company Pages)' },
                                    { id: 'bayt', label: 'Bayt' },
                                    { id: 'naukri', label: 'Naukri' },
                                    { id: 'bdjobs', label: 'Bdjobs' }
                                ].map(site => (
                                    <button
                                        key={site.id}
                                        type="button"
                                        onClick={() => {
                                            const current = params.sites ? params.sites.split(',') : [];
                                            let newSites;
                                            if (current.includes(site.id)) {
                                                newSites = current.filter(s => s !== site.id);
                                            } else {
                                                newSites = [...current, site.id];
                                            }
                                            setParams({ ...params, sites: newSites.join(',') });
                                        }}
                                        className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm transition-colors ${params.sites.split(',').includes(site.id)
                                            ? 'bg-blue-600 text-white border-blue-600'
                                            : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
                                            }`}
                                    >
                                        {params.sites.split(',').includes(site.id) && <Check size={14} />}
                                        {site.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Job Market <span className="text-gray-400 text-xs">(Country)</span>
                            </label>
                            <select
                                value={params.country}
                                onChange={e => setParams({ ...params, country: e.target.value })}
                                disabled={params.is_remote} // Optional: some users might want remote specific to a country
                                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none disabled:bg-gray-100 disabled:text-gray-400"
                            >
                                <option value="india">India</option>
                                <option value="usa">USA</option>
                                <option value="uk">UK</option>
                                <option value="canada">Canada</option>
                                <option value="australia">Australia</option>
                                <option value="germany">Germany</option>
                                <option value="france">France</option>
                                <option value="brazil">Brazil</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Experience</label>
                            <select
                                value={params.experience}
                                onChange={e => setParams({ ...params, experience: e.target.value })}
                                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                            >
                                <option value="">Any</option>
                                <option value="entry">Entry Level</option>
                                <option value="mid">Mid Level</option>
                                <option value="senior">Senior Level</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Job Type</label>
                            <select
                                value={params.job_type}
                                onChange={e => setParams({ ...params, job_type: e.target.value })}
                                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                            >
                                <option value="">Any</option>
                                <option value="fulltime">Full-time</option>
                                <option value="parttime">Part-time</option>
                                <option value="contract">Contract</option>
                                <option value="internship">Internship</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Date Posted</label>
                            <select
                                value={params.date_posted}
                                onChange={e => setParams({ ...params, date_posted: e.target.value })}
                                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                            >
                                <option value="">Anytime</option>
                                <option value="today">Past 24h</option>
                                <option value="3days">Past 3 Days</option>
                                <option value="week">Past Week</option>
                                <option value="month">Past Month</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Results</label>
                            <input
                                type="number"
                                value={params.results_wanted}
                                onChange={e => setParams({ ...params, results_wanted: e.target.value })}
                                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                            />
                        </div>
                    </div>
                    <div className="flex gap-6 pt-2">
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={params.is_remote}
                                onChange={e => setParams({ ...params, is_remote: e.target.checked })}
                                className="w-4 h-4 rounded text-blue-600"
                            />
                            <span className="text-sm text-gray-700">Remote Only</span>
                        </label>
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={params.easy_apply}
                                onChange={e => setParams({ ...params, easy_apply: e.target.checked })}
                                className="w-4 h-4 rounded text-blue-600"
                            />
                            <span className="text-sm text-gray-700">Easy Apply</span>
                        </label>
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2 mt-4"
                    >
                        {loading ? 'Searching...' : 'Search Jobs'}
                        {loading && <Loader2 className="animate-spin" size={18} />}
                        {!loading && <Search size={18} />}
                    </button>
                </form>
            </div>

            {/* Live Logs / CLI Output */}
            {logs.length > 0 && (
                <div className="bg-gray-900 rounded-lg border border-gray-700 mb-8 overflow-hidden shadow-lg">
                    <div className="bg-gray-800 px-4 py-2 flex justify-between items-center border-b border-gray-700">
                        <span className="text-xs text-gray-400 font-mono">JobSpy CLI Output</span>
                        {loading && <Loader2 size={14} className="text-green-500 animate-spin" />}
                    </div>
                    <div className="p-4 font-mono text-sm h-64 overflow-y-auto" ref={(el) => { if (el) el.scrollTop = el.scrollHeight; }}>
                        {logs.map((log, i) => (
                            <div key={i} className={`mb-1 ${log.includes('Error') ? 'text-red-400' : 'text-green-400'}`}>
                                <span className="text-gray-500 mr-2">$</span>
                                {log}
                            </div>
                        ))}
                        {loading && <div className="text-gray-500 animate-pulse">_</div>}
                    </div>
                </div>
            )}

            {/* Results Header */}
            {jobs.length > 0 && (
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-semibold text-gray-700">Found {jobs.length} Jobs</h3>
                    <button
                        onClick={handleSaveAll}
                        className="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg text-sm font-medium hover:bg-blue-200 flex items-center gap-2"
                    >
                        <Bookmark size={16} /> Save All
                    </button>
                </div>
            )}

            {/* Results */}
            <div className="space-y-4">
                {jobs.map(job => (
                    <div key={job.id} className="bg-white p-6 rounded-xl shadow-sm border hover:shadow-md transition-shadow">
                        <div className="flex justify-between items-start">
                            <div>
                                <h3 className="text-xl font-semibold text-blue-900">{job.title}</h3>
                                <div className="flex items-center gap-4 text-gray-600 mt-2 mb-3">
                                    <span className="flex items-center gap-1 font-medium">
                                        <Briefcase size={16} />
                                        {job.company}
                                    </span>
                                    <span className="flex items-center gap-1">
                                        <MapPin size={16} />
                                        {job.location}
                                    </span>
                                    <span className="flex items-center gap-1 capitalize text-xs bg-gray-100 px-2 py-1 rounded">
                                        <Globe size={14} />
                                        {job.site}
                                    </span>
                                </div>
                            </div>
                            <div className="flex flex-col items-end gap-2">
                                <div className="px-3 py-1 bg-green-50 text-green-700 rounded-full text-sm font-medium border border-green-100">
                                    Match: {job.match_score || 0}%
                                </div>
                            </div>
                        </div>

                        <p className="text-gray-600 line-clamp-3 mb-4 text-sm">{job.description_snippet}</p>

                        <div className="flex justify-between items-center border-t pt-4 mt-2">
                            <div className="flex gap-2 text-sm text-gray-500 overflow-x-auto">
                                {job.matching_skills && job.matching_skills.slice(0, 5).map(s => (
                                    <span key={s} className="px-2 py-1 bg-indigo-50 text-indigo-700 rounded text-xs">{s}</span>
                                ))}
                            </div>
                            <div className="flex gap-3 shrink-0">
                                <a
                                    href={job.job_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="px-4 py-2 border border-blue-200 text-blue-700 rounded-lg hover:bg-blue-50 flex items-center gap-2 text-sm font-medium"
                                >
                                    View Job <ExternalLink size={16} />
                                </a>

                                {tracking[job.job_url] === 'Saved' || tracking[job.job_url] === 'Applied' ? (
                                    <button
                                        disabled
                                        className="px-4 py-2 bg-green-100 text-green-700 rounded-lg flex items-center gap-2 text-sm font-medium"
                                    >
                                        <Check size={16} /> {tracking[job.job_url] || 'Saved'}
                                    </button>
                                ) : (
                                    <button
                                        onClick={() => trackJob(job, 'Saved')}
                                        disabled={tracking[job.job_url] === 'loading'}
                                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2 text-sm font-medium"
                                    >
                                        {tracking[job.job_url] === 'loading' ? <Loader2 className="animate-spin" size={16} /> : <Bookmark size={16} />}
                                        Save
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
                {jobs.length === 0 && !loading && (
                    <div className="text-center text-gray-500 py-12">
                        Start your search to find relevant jobs.
                    </div>
                )}
            </div>
        </div>
    );
}
