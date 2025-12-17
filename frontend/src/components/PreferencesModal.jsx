import { useState, useEffect } from 'react';
import { X, Save, Settings, Check } from 'lucide-react';

export default function PreferencesModal({ isOpen, onClose, onSave, initialPreferences = {} }) {
    const [prefs, setPrefs] = useState({
        country: 'india',
        is_remote: false,
        job_type: '',
        experience: '',
        results_wanted: 15,
        easy_apply: false,
        date_posted: '',
        sites: 'linkedin,indeed', // Default sites
        ...initialPreferences
    });

    // Reset when modal opens with new initials
    useEffect(() => {
        if (isOpen) {
            setPrefs({
                country: 'india',
                is_remote: false,
                job_type: '',
                experience: '',
                results_wanted: 15,
                easy_apply: false,
                date_posted: '',
                sites: 'linkedin,indeed',
                ...initialPreferences
            });
        }
    }, [isOpen, initialPreferences]);

    if (!isOpen) return null;

    const handleSubmit = (e) => {
        e.preventDefault();
        onSave(prefs);
        onClose();
    };

    const toggleSite = (site) => {
        const currentSites = prefs.sites ? prefs.sites.split(',') : [];
        let newSites;
        if (currentSites.includes(site)) {
            newSites = currentSites.filter(s => s !== site);
        } else {
            newSites = [...currentSites, site];
        }
        setPrefs({ ...prefs, sites: newSites.join(',') });
    };

    const availableSites = [
        { id: 'linkedin', label: 'LinkedIn' },
        { id: 'indeed', label: 'Indeed' },
        { id: 'glassdoor', label: 'Glassdoor' },
        { id: 'zip_recruiter', label: 'ZipRecruiter' },
        { id: 'google', label: 'Google', sub: '(Company Pages)' },
        { id: 'bayt', label: 'Bayt' },
        { id: 'naukri', label: 'Naukri' },
        { id: 'bdjobs', label: 'Bdjobs' },
        { id: 'remotive', label: 'Remotive' },
        { id: 'weworkremotely', label: 'WWR' },
        { id: 'workingnomads', label: 'Working Nomads' },
        { id: 'justremote', label: 'JustRemote' },
        { id: 'remote.co', label: 'Remote.co' },
        { id: 'powertofly', label: 'PowerToFly' },
        { id: 'remoteleaf', label: 'RemoteLeaf' },
        { id: 'jobspresso', label: 'Jobspresso' },
        { id: 'himalayas', label: 'Himalayas' },
        { id: 'jobicy', label: 'Jobicy' },
        { id: 'talent.com', label: 'Talent.com' },
        { id: 'jora', label: 'Jora' },
        { id: 'adzuna', label: 'Adzuna' },
    ];

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div
                className="bg-white rounded-xl shadow-xl w-full max-w-2xl transform transition-all scale-100 animate-in zoom-in-95 duration-200 overflow-hidden"
                role="dialog"
                aria-modal="true"
            >
                <div className="px-6 py-4 border-b flex justify-between items-center bg-gray-50">
                    <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                        <Settings className="text-blue-500" size={20} />
                        JobSpy Search Options
                    </h3>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-500 transition-colors p-1 rounded-full hover:bg-gray-200"
                    >
                        <X size={20} />
                    </button>
                </div>

                <form onSubmit={handleSubmit}>
                    <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">

                        <div className="md:col-span-2">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Job Platforms
                            </label>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                {availableSites.map(site => (
                                    <button
                                        key={site.id}
                                        type="button"
                                        onClick={() => toggleSite(site.id)}
                                        className={`flex items-center justify-between px-3 py-2 border rounded-lg text-sm transition-all ${prefs.sites.split(',').includes(site.id)
                                            ? 'bg-blue-50 border-blue-500 text-blue-700 shadow-sm'
                                            : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                                            }`}
                                    >
                                        <div className="flex flex-col items-start">
                                            <span>{site.label}</span>
                                            {site.sub && <span className="text-[10px] text-gray-400">{site.sub}</span>}
                                        </div>
                                        {prefs.sites.split(',').includes(site.id) && <Check size={14} />}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Job Market (Country)
                            </label>
                            <select
                                value={prefs.country}
                                onChange={e => setPrefs({ ...prefs, country: e.target.value })}
                                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
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
                            <label className="block text-sm font-medium text-gray-700 mb-1">Experience Level</label>
                            <select
                                value={prefs.experience}
                                onChange={e => setPrefs({ ...prefs, experience: e.target.value })}
                                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
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
                                value={prefs.job_type}
                                onChange={e => setPrefs({ ...prefs, job_type: e.target.value })}
                                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
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
                                value={prefs.date_posted}
                                onChange={e => setPrefs({ ...prefs, date_posted: e.target.value })}
                                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                            >
                                <option value="">Anytime</option>
                                <option value="today">Past 24h</option>
                                <option value="3days">Past 3 Days</option>
                                <option value="week">Past Week</option>
                                <option value="month">Past Month</option>
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Results per Search</label>
                            <input
                                type="number"
                                value={prefs.results_wanted}
                                onChange={e => setPrefs({ ...prefs, results_wanted: e.target.value })}
                                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                min="1"
                                max="50"
                            />
                        </div>

                        <div className="flex flex-col justify-center gap-3">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={prefs.is_remote}
                                    onChange={e => setPrefs({ ...prefs, is_remote: e.target.checked })}
                                    className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500"
                                />
                                <span className="text-sm text-gray-700">Remote Only</span>
                            </label>

                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={prefs.easy_apply}
                                    onChange={e => setPrefs({ ...prefs, easy_apply: e.target.checked })}
                                    className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500"
                                />
                                <span className="text-sm text-gray-700">Easy Apply</span>
                            </label>
                        </div>
                    </div>

                    <div className="px-6 py-4 bg-gray-50 flex justify-end gap-3">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-white hover:border-gray-400 transition-colors font-medium bg-white"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 font-medium shadow-sm transition-colors"
                        >
                            <Save size={18} />
                            Save Preferences
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
