function run_tests()
%RUN_TESTS Runs the complete MATLAB geometry compiler test suite
%   RUN_TESTS adds project subdirectories to MATLAB path and executes
%   all unit tests found in the tests/ directory.
%
%   This function locates the project root from its own file location
%   (via mfilename) so it works correctly in any worktree.
%
%   Example:
%       run_tests();
%
%   See also: runtests

    % Derive project root from this file's location
    thisPath = mfilename('fullpath');
    base_dir = fileparts(strrep(thisPath, '\', '/'));

    % Add core functions directory
    core_path = fullfile(base_dir, 'core');
    if ~exist(core_path, 'dir')
        error('Core directory not found: %s', core_path);
    end
    addpath(core_path);

    % Add config directory for descriptor definitions
    config_path = fullfile(base_dir, 'configs');
    if ~exist(config_path, 'dir')
        error('Config directory not found: %s', config_path);
    end
    addpath(config_path);

    % Add tests directory
    tests_path = fullfile(base_dir, 'tests');
    if ~exist(tests_path, 'dir')
        error('Tests directory not found: %s', tests_path);
    end
    addpath(tests_path);

    % Run ALL tests in the tests/ directory (not just TestBootstrap)
    results = runtests(tests_path);

    % Assert all tests passed
    if ~all([results.Passed])
        failed_count = sum([results.Failed]);
        total_count = length(results);
        error('Unit tests failed: %d out of %d tests failed', failed_count, total_count);
    end

    fprintf('\nAll bootstrap tests passed successfully!\n');
    fprintf('Total tests: %d, Passed: %d, Failed: %d\n', ...
        length(results), sum([results.Passed]), sum([results.Failed]));

end
