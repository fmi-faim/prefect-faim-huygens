import os
import subprocess
from pathlib import Path
from typing import List

import faim_prefect.io
from faim_huygens.parameters import create_config, Deconvolution, Microscopy
from faim_huygens.templates import write_template
from faim_prefect.block.choices import Choices
from prefect import flow, get_run_logger, task, unmapped
from prefect.context import get_run_context
from prefect.filesystems import LocalFileSystem
from tempfile import TemporaryDirectory

Groups = Choices.load('fmi-groups').get()


def deconvolve_file(
        hucore_path: str,
        input_file: str,
        temp_dir: str,
        output_dir: str,
        microscope_params: Microscopy,
        deconvolution_params: Deconvolution,
):
    config = create_config(input_files=[input_file], result_dir=output_dir, microscopy_params=microscope_params,
                           deconvolution_params=deconvolution_params)
    template_file = Path(temp_dir, Path(input_file).stem + '_template.hgsb')
    write_template(output_file=template_file, config=config)
    process = subprocess.run(
        [hucore_path, "-noExecLog", "-exitOnDone", "-checkUpdates", "disable", "-hdbc", "-hdbt", "-template",
         str(template_file)])
    process.check_returncode()
    get_run_logger().info(f"Success. Deconvolution finished.")


@flow(name="Huygens Deconvolution")
def deconvolve(
        username: str,
        group: Groups,
        input_files: List[str],
        microscope_params: Microscopy,
        deconvolution_params: Deconvolution
):
    context = get_run_context()
    hucore_path = os.getenv('HUCORE_PATH') or 'hucore'
    output_folder = faim_prefect.io.create_output_dir(LocalFileSystem.load("base-output-directory").basepath,
                                                      group.value,
                                                      username, context.flow.name)
    with TemporaryDirectory() as tempdir:
        # process files sequentially, one 'hucore' process at a time
        for f in input_files:
            deconvolve_file(
                hucore_path,
                f,
                tempdir,
                output_folder,
                microscope_params,
                deconvolution_params
            )


if __name__ == "__main__":
    deconvolve(
        'user',
        Groups.gmicro,
        ['/path/to/image1.ome.tif',
         '/path/to/image2.ome.tif',
         ],
        Microscopy(scale_z=0.1), Deconvolution())