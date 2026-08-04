function version = compiler_version()
%COMPILER_VERSION Returns the MATLAB geometry compiler version string
%   VERSION = COMPILER_VERSION returns the exact version identifier for
%   the graded Gyroid geometry compiler built on MATLAB R2023b.
%
%   This function provides a stable version string used for:
%   - Compiler contract validation
%   - Configuration compatibility checking
%   - Reproducibility tracking in research workflows
%
%   Example:
%       v = compiler_version();
%       % Returns: v = 'matlab-gyroid-0.2.0'
%
%   See also: load_compiler_config

    version = 'matlab-gyroid-0.2.0';
end
