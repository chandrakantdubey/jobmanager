import { useState, useContext, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Globe, Loader2, CheckCircle2, XCircle, ArrowRight, Play } from 'lucide-react';
import api from '../api';
import { AuthContext } from '../context/AuthContext';
import toast from 'react-hot-toast';

export default function SearchPage() {
    const { token } = useContext(AuthContext);
    const navigate = useNavigate();
    const [params, setParams] = useState({
        search_term: 'Python Developer',
        location: 'India',
        results_wanted: 20,
        sites: 'linkedin,indeed',
        is_remote: false,
        country: 'india',
    });

    const [loading, setLoading] = useState(false);
    const [logs, setLogs] = useState([]);
    const [jobsFound, setJobsFound] = useState(0);
    const [searchComplete, setSearchComplete] = useState(false);
    const abortControllerRef = useRef(null);
    const [activeResume, setActiveResume] = useState(null);

    useEffect(() => {
        const fetchResume = async () => {
            try {
                const res = await api.get('/resumes/active');
                setActiveResume(res.data);

                // Pre-fill search term and preferences
                let newTerm = params.search_term;
                if (res.data.parsed_titles && res.data.parsed_titles.length > 0 && params.search_term === 'Python Developer') {
                    newTerm = res.data.parsed_titles[0];
                }

                let newParams = { ...params, search_term: newTerm };
                if (res.data.search_preferences && Object.keys(res.data.search_preferences).length > 0) {
                    newParams = { ...newParams, ...res.data.search_preferences };
                }
                setParams(newParams);
            } catch (err) {
                console.log('No active resume found.');
            }
        };
        fetchResume();
    }, []);

    const handleSearch = async (e) => {
        e.preventDefault();
        setLoading(true);
        setLogs([]);
        setJobsFound(0);
        setSearchComplete(false);

        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
        abortControllerRef.current = new AbortController();

        const searchParams = new URLSearchParams();
        Object.keys(params).forEach(key => {
            if (params[key] !== '') searchParams.append(key, params[key]);
        });
        searchParams.append('token', token);

        try {
            const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/search/stream?${searchParams.toString()}`, {
                signal: abortControllerRef.current.signal
            });

            if (!response.ok) throw new Error('Search failed');

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\\n');

                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const data = JSON.parse(line);
                        if (data.type === 'update') {
                            setLogs(prev => [...prev, { type: 'info', message: data.message }]);
                        } else if (data.type === 'result_batch') {
                            const count = data.data.length;
                            setJobsFound(prev => prev + count);
                            setLogs(prev => [...prev, { type: 'success', message: `✓ Saved ${count} jobs to database` }]);
                        } else if (data.type === 'error') {
                            setLogs(prev => [...prev, { type: 'error', message: `✗ ${data.message}` }]);
                        }
                    } catch (e) {
                        console.error('Error parsing stream:', e);
                    }
                }
            }

            setSearchComplete(true);
            toast.success(`Search complete! Found ${jobsFound} jobs`);
        } catch (err) {
            if (err.name !== 'AbortError') {
                console.error(err);
                setLogs(prev => [...prev, {
                    type: 'error', message: 'Search failed. Please try again.'
                }]);
                toast.error('Search failed');
            }
        } finally {
            setLoading(false);
        }
    };

    const handleStop = () => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            setLoading(false);
            setLogs(prev => [...prev, {
                type: 'info', message: 'Search stopped by user'
            }]);
        }
    };

    const SITE_GROUPS = {
        'Major Job Boards': ['linkedin', 'indeed', 'glassdoor', 'ziprecruiter'],
        'Remote-Focused': ['remotive', 'himalayas', 'weworkremotely', 'remote.co', 'workingnomads', 'justremote', 'remoteleaf', 'jobspresso', 'powertofly', 'skipthedrive'],
        'Freelance/Gig Platforms': ['peopleperhour', 'guru', 'truelancer'],
        'Startup Jobs': ['builtin', 'themuse'],
        'Tech/Developer Focused': ['arc', 'dice'],
        'General Job Aggregators': ['jora', 'adzuna', 'talent.com'],
        'Other/Custom': ['google', 'bayt', 'naukri']
    };

    const toggleSite = (siteName) => {
        const current = params.sites ? params.sites.split(',') : [];
        let newSites;
        if (current.includes(siteName)) {
            newSites = current.filter(s => s !== siteName);
        } else {
            newSites = [...current, siteName];
        }
        setParams(p => ({ ...p, sites: newSites.join(',') }));
    };

    const toggleGroup = (groupName) => {
        const groupSites = SITE_GROUPS[groupName];
        const current = params.sites ? params.sites.split(',') : [];
        const allSelected = groupSites.every(site => current.includes(site));

        if (allSelected) {
            // Deselect all
            const newSites = current.filter(s => !groupSites.includes(s));
            setParams(p => ({ ...p, sites: newSites.join(',') }));
        } else {
            // Select all
            const newSites = [...new Set([...current, ...groupSites])];
            setParams(p => ({ ...p, sites: newSites.join(',') }));
        }
    };

    return (
        <div className='max-w-7xl mx-auto'>
            < div className='mb-8'>
                < h1 className='text-3xl font-bold text-gray-900 mb-2'>
                    Find Jobs
                </h1 >
                <p className='text-gray-600'>
                    Search and scrape jobs from 26 + platforms - results will be saved to Scraped Jobs
                </p >
            </div >

            {/* Search Form */}
            < form onSubmit={handleSearch} className='bg-white rounded-xl shadow-sm border p-6 mb-6'>
                < div className='grid grid-cols-1 md:grid-cols-2 gap-4 mb-4'>
                    < div >
                        <label className='block text-sm font-medium text-gray-700 mb-2'>
                            Search Term
                        </label >
                        <input
                            type='text'
                            value={params.search_term}
                            onChange={(e) => setParams({ ...params, search_term: e.target.value })}
                            className='w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                            placeholder='e.g. Python Developer'
                            required
                        />
                    </div >
                    <div>
                        <label className='block text-sm font-medium text-gray-700 mb-2'>
                            Location
                        </label>
                        <input
                            type='text'
                            value={params.location}
                            onChange={(e) => setParams({ ...params, location: e.target.value })}
                            className='w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                            placeholder='e.g. India, Remote'
                            required
                        />
                    </div >
                </div >

                <div className='grid grid-cols-1 md:grid-cols-3 gap-4 mb-6'>
                    < div >
                        <label className='block text-sm font-medium text-gray-700 mb-2'>
                            Results Per Site
                        </label >
                        <input
                            type='number'
                            value={params.results_wanted}
                            onChange={(e) => setParams({ ...params, results_wanted: parseInt(e.target.value) })}
                            className='w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                            min='5'
                            max='100'
                        />
                    </div >
                    <div>
                        <label className='block text-sm font-medium text-gray-700 mb-2'>
                            Country
                        </label>
                        <select
                            value={params.country}
                            onChange={(e) => setParams({ ...params, country: e.target.value })}
                            className='w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                        >
                            <option value='india'>India</option>
                            < option value='usa'>USA</option>
                            < option value='uk'>UK</option>
                            < option value='canada'>Canada</option>
                            < option value='australia'>Australia</option>
                        </select >
                    </div >
                    <div className='flex items-end'>
                        < label className='flex items-center space-x-2 cursor-pointer'>
                            < input
                                type='checkbox'
                                checked={params.is_remote}
                                onChange={(e) => setParams({ ...params, is_remote: e.target.checked })}
                                className='w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500'
                            />
                            <span className='text-sm font-medium text-gray-700'>Remote Only</span>
                        </label >
                    </div >
                </div >

                {/* Site Selection */}
                < div className='mb-6'>
                    < label className='block text-sm font-medium text-gray-700 mb-3'>
                        Select Job Sites({params.sites.split(',').filter(s => s).length} selected)
                    </label >
                    <div className='space-y-4'>
                        {
                            Object.entries(SITE_GROUPS).map(([groupName, groupSites]) => {
                                const current = params.sites ? params.sites.split(',') : [];
                                const selectedCount = groupSites.filter(site => current.includes(site)).length;
                                const allSelected = selectedCount === groupSites.length;

                                return (
                                    <div key={groupName} className='border rounded-lg p-4'>
                                        < div className='flex items-center justify-between mb-3'>
                                            < button
                                                type='button'
                                                onClick={() => toggleGroup(groupName)
                                                }
                                                className='text-sm font-semibold text-gray-700 hover:text-blue-600'
                                            >
                                                {groupName}({selectedCount} / {groupSites.length})
                                            </button >
                                            <button
                                                type='button'
                                                onClick={() => toggleGroup(groupName)}
                                                className='text-xs px-3 py-1 bg-gray-100 hover:bg-blue-100 rounded'
                                            >
                                                {allSelected ? 'Deselect All' : 'Select All'}
                                            </button >
                                        </div >
                                        <div className='flex flex-wrap gap-2'>
                                            {
                                                groupSites.map(site => (
                                                    <button
                                                        key={site}
                                                        type='button'
                                                        onClick={() => toggleSite(site)}
                                                        className={`px-3 py-1 text-xs rounded-full transition-colors ${current.includes(site)
                                                            ? 'bg-blue-600 text-white'
                                                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                                            }`}
                                                    >
                                                        {site}
                                                    </button >
                                                ))}
                                        </div >
                                    </div >
                                );
                            })}
                    </div >
                </div >

                {/* Search Button */}
                < div className='flex gap-4'>
                    < button
                        type='submit'
                        disabled={loading || !params.sites}
                        className='flex-1 bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center gap-2'
                    >
                        {
                            loading ? (
                                <>
                                    <Loader2 className='animate-spin' size={20} />
                                    Searching...
                                </>
                            ) : (
                                <>
                                    <Play size={20} />
                                    Start Search
                                </>
                            )}
                    </button >
                    {loading && (
                        <button
                            type='button'
                            onClick={handleStop}
                            className='px-6 py-3 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700'
                        >
                            Stop
                        </button >
                    )}
                </div >
            </form >

            {/* Streaming Progress */}
            {
                (loading || logs.length > 0) && (
                    <div className='bg-white rounded-xl shadow-sm border mb-6'>
                        < div className='p-6 border-b'>
                            < div className='flex items-center justify-between'>
                                < h2 className='text-xl font-semibold text-gray-900'>
                                    Search Progress
                                </h2 >
                                <div className='flex items-center gap-4'>
                                    < div className='text-sm font-medium text-gray-600'>
                                        Jobs Found: <span className='text-2xl font-bold text-blue-600'>{jobsFound}</span>
                                    </div >
                                    {searchComplete && (
                                        <CheckCircle2 className='text-green-600' size={24} />
                                    )
                                    }
                                </div >
                            </div >
                        </div >

                        {/* Live Logs */}
                        < div className='p-6 max-h-96 overflow-y-auto bg-gray-50'>
                            < div className='space-y-2 font-mono text-sm'>
                                {
                                    logs.map((log, idx) => (
                                        <div
                                            key={idx}
                                            className={`flex items-start gap-2 ${log.type === 'error' ? 'text-red-600' :
                                                    log.type === 'success' ? 'text-green-600' :
                                                        'text-gray-700'
                                                }`}
                                        >
                                            <span className='text-gray-400'>›</span>
                                            <span>{log.message}</span>
                                        </div >
                                    ))
                                }
                                {
                                    loading && (
                                        <div className='flex items-center gap-2 text-blue-600'>
                                            < Loader2 className='animate-spin' size={16} />
                                            < span > Searching...</span >
                                        </div >
                                    )
                                }
                            </div >
                        </div >

                        {/* View Results Button */}
                        {
                            searchComplete && jobsFound > 0 && (
                                <div className='p-6 border-t bg-gradient-to-r from-green-50 to-blue-50'>
                                    < button
                                        onClick={() => navigate('/scraped')
                                        }
                                        className='w-full bg-green-600 text-white py-4 px-6 rounded-lg font-semibold hover:bg-green-700 flex items-center justify-center gap-2'
                                    >
                                        <Globe size={20} />
                                        View {jobsFound} Scraped Jobs
                                        < ArrowRight size={20} />
                                    </button >
                                </div >
                            )}
                    </div >
                )}
        </div >
    );
}
